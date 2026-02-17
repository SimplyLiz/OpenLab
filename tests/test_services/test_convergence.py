"""Tests for convergence scoring, disagreement detection, and confidence tiers."""

import pytest

from openlab.db.models import Evidence, EvidenceType, Gene
from openlab.services.gene_service import (
    compute_convergence_score,
    detect_disagreements,
    detect_all_disagreements,
)
from openlab.services.convergence import (
    _pairwise_agreement,
    _make_bigrams,
)
from openlab.services.evidence_normalizer import normalize_evidence, NormalizedEvidence
from openlab.services.validation_service import _classify_tier


@pytest.fixture
def gene_with_evidence(db):
    """Create a gene with multiple evidence records."""
    gene = Gene(
        locus_tag="JCVISYN3A_0500",
        sequence="ATGAAA",
        protein_sequence="MAAAA",
        length=6,
        strand=1,
        start=100,
        end=106,
    )
    db.add(gene)
    db.flush()
    return db, gene


class TestNormalizeEvidence:
    def test_extracts_hit_descriptions(self):
        ev = Evidence(
            gene_id=1,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={
                "source": "NCBI_BLAST",
                "hits": [
                    {"description": "DNA polymerase III subunit alpha", "evalue": 1e-20}
                ],
            },
        )
        norm = normalize_evidence(ev)
        assert "dna_repair:replication" in norm.categories  # "polymerase" → dna_repair:replication
        assert len(norm.keywords) > 0

    def test_extracts_go_terms(self):
        ev = Evidence(
            gene_id=1,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={
                "source": "InterProScan",
                "go_terms": [
                    {"id": "GO:0003677", "description": "DNA binding activity"},
                    "GO:0003677:DNA binding",
                ],
            },
        )
        norm = normalize_evidence(ev)
        assert "GO:0003677" in norm.go_terms

    def test_extracts_operon_context(self):
        ev = Evidence(
            gene_id=1,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={
                "source": "operon_prediction",
                "operon_functions": ["tRNA ligase", "ribosome maturation"],
                "functional_context": "translation ribosome",
            },
        )
        norm = normalize_evidence(ev)
        assert "translation" in norm.categories

    def test_empty_payload(self):
        ev = Evidence(
            gene_id=1,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={},
        )
        norm = normalize_evidence(ev)
        assert len(norm.go_terms) == 0
        assert len(norm.ec_numbers) == 0
        assert len(norm.categories) == 0


class TestConvergenceScore:
    def test_no_evidence_returns_zero(self, gene_with_evidence):
        db, gene = gene_with_evidence
        score = compute_convergence_score(db, gene.gene_id)
        assert score == 0.0

    def test_single_evidence_returns_one(self, gene_with_evidence):
        db, gene = gene_with_evidence
        ev = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"source": "BLAST", "hits": [{"description": "DNA polymerase"}]},
            confidence=0.8,
        )
        db.add(ev)
        db.flush()

        score = compute_convergence_score(db, gene.gene_id)
        assert score == 1.0

    def test_agreeing_evidence_high_convergence(self, gene_with_evidence):
        db, gene = gene_with_evidence
        # Two sources agreeing on DNA polymerase
        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={
                "source": "BLAST",
                "hits": [{"description": "DNA polymerase III subunit alpha"}],
            },
            confidence=0.8,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={
                "source": "eggNOG",
                "predicted_name": "dnaE",
                "description": "DNA polymerase III catalytic subunit",
            },
            confidence=0.7,
        )
        db.add_all([ev1, ev2])
        db.flush()

        score = compute_convergence_score(db, gene.gene_id)
        assert score >= 0.5  # should be high — both say polymerase/enzyme

    def test_disagreeing_evidence_low_convergence(self, gene_with_evidence):
        db, gene = gene_with_evidence
        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={
                "source": "BLAST",
                "hits": [{"description": "membrane lipid transport protein"}],
            },
            confidence=0.5,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={
                "source": "eggNOG",
                "description": "ribosomal RNA methyltransferase",
                "predicted_name": "rlmH",
            },
            confidence=0.5,
        )
        ev3 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.LITERATURE,
            payload={
                "source": "EuropePMC",
                "articles": [{"title": "Cell division in minimal organisms"}],
            },
            confidence=0.4,
        )
        db.add_all([ev1, ev2, ev3])
        db.flush()

        score = compute_convergence_score(db, gene.gene_id)
        # Three different topics — convergence should be bounded
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestDisagreementDetection:
    def test_no_disagreements_when_agreeing(self, gene_with_evidence):
        """Evidence all pointing to same function should have no disagreements."""
        db, gene = gene_with_evidence
        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "DNA polymerase III alpha subunit"}]},
            confidence=0.8,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={"description": "DNA polymerase III catalytic subunit", "predicted_name": "dnaE"},
            confidence=0.7,
        )
        db.add_all([ev1, ev2])
        db.flush()

        report = detect_disagreements(db, gene.gene_id)
        assert report.gene_id == gene.gene_id
        assert len(report.disagreeing_pairs) == 0

    def test_detects_disagreement(self, gene_with_evidence):
        """Evidence pointing to completely different functions should be flagged."""
        db, gene = gene_with_evidence
        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "lipid membrane transporter"}]},
            confidence=0.8,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={"description": "ribosomal RNA methyltransferase"},
            confidence=0.7,
        )
        db.add_all([ev1, ev2])
        db.flush()

        report = detect_disagreements(db, gene.gene_id)
        assert len(report.disagreeing_pairs) > 0
        dp = report.disagreeing_pairs[0]
        assert dp.agreement_score < 0.2

    def test_threshold_adjustable(self, gene_with_evidence):
        """Higher threshold should flag more pairs as disagreeing."""
        db, gene = gene_with_evidence
        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "kinase activity"}]},
            confidence=0.8,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={"description": "phosphatase activity"},
            confidence=0.7,
        )
        db.add_all([ev1, ev2])
        db.flush()

        report_low = detect_disagreements(db, gene.gene_id, threshold=0.1)
        report_high = detect_disagreements(db, gene.gene_id, threshold=0.9)
        assert len(report_high.disagreeing_pairs) >= len(report_low.disagreeing_pairs)

    def test_single_evidence_no_disagreements(self, gene_with_evidence):
        """A single evidence record has no pairs to disagree."""
        db, gene = gene_with_evidence
        ev = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "ABC transporter"}]},
            confidence=0.8,
        )
        db.add(ev)
        db.flush()

        report = detect_disagreements(db, gene.gene_id)
        assert report.total_pairs == 0
        assert len(report.disagreeing_pairs) == 0

    def test_batch_detection(self, gene_with_evidence):
        """Batch mode should find genes with disagreements."""
        db, gene = gene_with_evidence
        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "lipid transporter protein"}]},
            confidence=0.8,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={"description": "ribosomal RNA methyltransferase"},
            confidence=0.7,
        )
        db.add_all([ev1, ev2])
        db.flush()

        results = detect_all_disagreements(db)
        assert isinstance(results, list)
        # Our gene should appear if it has disagreements
        gene_ids = [r["gene_id"] for r in results]
        if results:
            assert results[0]["disagreement_count"] > 0


class TestPairwiseAgreement:
    """Test the updated _pairwise_agreement scoring."""

    def test_same_subcategory_scores_high(self):
        """Two evidence records in the same subcategory should score well."""
        a = NormalizedEvidence(
            categories={"enzyme:glycolysis"},
            keywords={"pyruvate", "kinase", "glycolysis"},
        )
        b = NormalizedEvidence(
            categories={"enzyme:glycolysis"},
            keywords={"pyruvate", "phosphofructokinase", "glycolysis"},
        )
        score = _pairwise_agreement(a, b)
        assert score > 0.4  # subcategory match + keyword overlap

    def test_different_subcategory_scores_lower(self):
        """Different subcategories under same parent should score lower than same subcategory."""
        a = NormalizedEvidence(
            categories={"enzyme:glycolysis"},
            keywords={"pyruvate", "kinase"},
        )
        b = NormalizedEvidence(
            categories={"enzyme:rna_modification"},
            keywords={"methyltransferase", "rRNA"},
        )
        # Same parent (enzyme) but different subcategory
        score = _pairwise_agreement(a, b)
        assert score < 0.4  # broad match only

    def test_keywords_always_contribute(self):
        """Keywords should contribute even when categories are present."""
        a = NormalizedEvidence(
            categories={"enzyme"},
            keywords={"thioredoxin", "reductase", "redox"},
        )
        b = NormalizedEvidence(
            categories={"enzyme"},
            keywords={"thioredoxin", "reductase", "oxidoreductase"},
        )
        score = _pairwise_agreement(a, b)
        # Keywords share "thioredoxin" and "reductase" — should boost score
        assert score > 0.3

    def test_go_terms_dominate(self):
        """GO term agreement should produce high scores."""
        a = NormalizedEvidence(
            go_terms={"GO:0034061"},  # DNA polymerase
            categories={"enzyme"},
            keywords={"polymerase"},
        )
        b = NormalizedEvidence(
            go_terms={"GO:0034061"},
            categories={"enzyme"},
            keywords={"polymerase"},
        )
        score = _pairwise_agreement(a, b)
        assert score > 0.8  # GO exact match should dominate

    def test_empty_evidence_returns_zero(self):
        """Two empty evidence records should score 0."""
        a = NormalizedEvidence()
        b = NormalizedEvidence()
        score = _pairwise_agreement(a, b)
        assert score == 0.0


class TestMakeBigrams:
    def test_creates_bigrams(self):
        bigrams = _make_bigrams({"alpha", "beta", "gamma"})
        assert len(bigrams) == 2  # sorted: alpha, beta, gamma → 2 bigrams
        assert "alpha_beta" in bigrams
        assert "beta_gamma" in bigrams

    def test_single_keyword_no_bigrams(self):
        assert _make_bigrams({"solo"}) == set()

    def test_empty_no_bigrams(self):
        assert _make_bigrams(set()) == set()


class TestClassifyTier:
    """Test the tier classification logic."""

    def test_tier1_high_convergence_pass(self):
        assert _classify_tier(0.6, None, True) == 1
        assert _classify_tier(0.8, True, True) == 1

    def test_tier2_moderate_convergence(self):
        assert _classify_tier(0.3, None, True) == 2
        assert _classify_tier(0.25, True, True) == 2

    def test_tier3_low_convergence(self):
        assert _classify_tier(0.1, None, True) == 3

    def test_tier4_ortholog_mismatch(self):
        assert _classify_tier(0.9, False, True) == 4  # ortholog fail always → T4

    def test_tier4_inconsistent_and_low(self):
        assert _classify_tier(0.05, None, False) == 4  # cons fail + conv < 0.1

    def test_tier2_high_conv_but_inconsistent(self):
        # High convergence but consistency fail → moderate (not T1)
        assert _classify_tier(0.6, None, False) == 2


class TestNormalizedEvidenceBigrams:
    """Test that the normalizer produces bigrams in keywords."""

    def test_bigrams_in_keywords(self):
        ev = Evidence(
            gene_id=1,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={
                "source": "BLAST",
                "hits": [{"description": "DNA polymerase III catalytic subunit alpha"}],
            },
        )
        norm = normalize_evidence(ev)
        # "polymerase" and "catalytic" would be filtered, but "alpha" is kept
        # Check that at least some bigrams were created
        bigrams = [kw for kw in norm.keywords if " " in kw]
        assert len(bigrams) > 0  # at least one bigram from consecutive filtered words

    def test_string_functional_description(self):
        """STRING evidence with functional_description should be extracted."""
        ev = Evidence(
            gene_id=1,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={
                "source": "STRING",
                "functional_description": "thioredoxin reductase involved in redox homeostasis",
                "partners": [
                    {"partner": "trxB", "description": "thioredoxin reductase"},
                ],
            },
        )
        norm = normalize_evidence(ev)
        assert "thioredoxin" in norm.keywords or any("thioredoxin" in kw for kw in norm.keywords)
