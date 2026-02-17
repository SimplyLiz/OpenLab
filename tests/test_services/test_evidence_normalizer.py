"""Tests for evidence normalizer — GO term extraction, EC numbers, keyword mapping."""

import pytest

from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.services.evidence_normalizer import (
    NormalizedEvidence,
    normalize_evidence,
    reset_keyword_map_cache,
    _extract_ec_numbers,
    _extract_go_terms,
    _map_keywords_to_go,
)
from openlab.services.gene_service import compute_convergence_score
from openlab.services.convergence import _pairwise_agreement


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset keyword map cache before each test."""
    reset_keyword_map_cache()
    yield
    reset_keyword_map_cache()


def _make_evidence(evidence_type, payload):
    """Create an Evidence-like object without DB persistence."""
    class FakeEvidence:
        pass
    ev = FakeEvidence()
    ev.evidence_type = evidence_type
    ev.payload = payload
    ev.gene_id = 1
    ev.confidence = 0.8
    ev.quality_score = 0.7
    return ev


# --- EC number extraction ---

class TestExtractECNumbers:
    def test_standard_ec(self):
        assert _extract_ec_numbers("EC 2.7.1.1 phosphofructokinase") == {"2.7.1.1"}

    def test_partial_ec(self):
        assert _extract_ec_numbers("EC 3.1.3.-") == {"3.1.3.-"}

    def test_multiple_ec(self):
        result = _extract_ec_numbers("Has 2.7.1.1 and 4.2.1.11 activities")
        assert result == {"2.7.1.1", "4.2.1.11"}

    def test_no_ec(self):
        assert _extract_ec_numbers("hypothetical protein") == set()


# --- GO term extraction ---

class TestExtractGOTerms:
    def test_standard_go(self):
        assert _extract_go_terms("GO:0005524 ATP binding") == {"GO:0005524"}

    def test_multiple_go(self):
        result = _extract_go_terms("GO:0003677 DNA binding GO:0006260 replication")
        assert result == {"GO:0003677", "GO:0006260"}

    def test_no_go(self):
        assert _extract_go_terms("hypothetical protein") == set()


# --- Keyword → GO mapping ---

class TestKeywordMapping:
    def test_kinase(self):
        go_terms, cats = _map_keywords_to_go("protein kinase activity")
        assert "GO:0016301" in go_terms
        assert "enzyme" in cats

    def test_transporter(self):
        go_terms, cats = _map_keywords_to_go("ABC transporter permease")
        assert "GO:0005215" in go_terms
        assert "transporter" in cats

    def test_ribosomal(self):
        go_terms, cats = _map_keywords_to_go("50S ribosomal protein L2")
        assert "GO:0003735" in go_terms or "GO:0015934" in go_terms
        assert any(c.startswith("translation") for c in cats)

    def test_no_match(self):
        go_terms, cats = _map_keywords_to_go("xyzzy foo bar")
        assert len(go_terms) == 0
        assert len(cats) == 0


# --- Full normalization ---

class TestNormalizeEvidence:
    def test_blast_hit_with_ec(self):
        ev = _make_evidence(EvidenceType.HOMOLOGY, {
            "hits": [
                {"description": "Phosphofructokinase EC 2.7.1.11", "name": "pfkA"},
            ],
        })
        norm = normalize_evidence(ev)
        assert "2.7.1.11" in norm.ec_numbers
        assert any(c.startswith("enzyme") for c in norm.categories)

    def test_uniprot_with_go_terms(self):
        ev = _make_evidence(EvidenceType.HOMOLOGY, {
            "protein_name": "DNA helicase",
            "go_terms": [
                {"id": "GO:0004386", "description": "helicase activity"},
            ],
        })
        norm = normalize_evidence(ev)
        assert "GO:0004386" in norm.go_terms
        assert any(c.startswith("dna_repair") for c in norm.categories)  # helicase → dna_repair:replication

    def test_string_partners(self):
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "partners": [
                {"partner": "dnaA", "annotation": "chromosomal replication"},
            ],
        })
        norm = normalize_evidence(ev)
        assert any(c.startswith("dna_repair") for c in norm.categories)

    def test_operon_context(self):
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "operon_functions": ["ribosomal protein", "translation factor"],
            "functional_context": "translation machinery",
        })
        norm = normalize_evidence(ev)
        assert "translation" in norm.categories

    def test_curated_reclassification(self):
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "predicted_function": "membrane transporter",
        })
        norm = normalize_evidence(ev)
        assert "transporter" in norm.categories
        assert "membrane_biogenesis" in norm.categories

    def test_empty_payload(self):
        ev = _make_evidence(EvidenceType.HOMOLOGY, {})
        norm = normalize_evidence(ev)
        assert len(norm.go_terms) == 0
        assert len(norm.ec_numbers) == 0
        assert len(norm.categories) == 0

    def test_go_string_format(self):
        ev = _make_evidence(EvidenceType.HOMOLOGY, {
            "go_terms": ["GO:0004386:helicase activity"],
        })
        norm = normalize_evidence(ev)
        assert "GO:0004386" in norm.go_terms

    def test_literature_articles(self):
        ev = _make_evidence(EvidenceType.LITERATURE, {
            "articles": [
                {"title": "A novel kinase in Mycoplasma cell division"},
            ],
        })
        norm = normalize_evidence(ev)
        assert "enzyme" in norm.categories or "cell_division" in norm.categories


# --- Pairwise agreement ---

class TestInterProScanMatches:
    def test_interproscan_matches_extraction(self):
        """InterProScan matches[].description should be extracted."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "InterProScan",
            "matches": [
                {
                    "name": "PF00005",
                    "description": "ABC transporter-like",
                    "go_terms": [
                        {"id": "GO:0042626", "description": "ATPase-coupled transmembrane transporter"},
                    ],
                },
                {
                    "name": "IPR003439",
                    "description": "AAA+ ATPase domain",
                },
            ],
        })
        norm = normalize_evidence(ev)
        assert "GO:0042626" in norm.go_terms
        assert "transporter" in norm.categories or "enzyme" in norm.categories
        assert len(norm.keywords) > 0

    def test_interproscan_go_term_string_format(self):
        """InterProScan matches with GO terms as strings."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "matches": [
                {
                    "description": "kinase domain",
                    "go_terms": ["GO:0016301:kinase activity"],
                },
            ],
        })
        norm = normalize_evidence(ev)
        assert "GO:0016301" in norm.go_terms


class TestNeighborhoodInferredContext:
    def test_inferred_context_extraction(self):
        """Neighborhood inferred_context should contribute keywords."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "genomic_neighborhood",
            "neighbors": [
                {"product": "hypothetical protein"},
            ],
            "inferred_context": "Flanked by: Flavin reductase, PolC-type DNA polymerase III",
        })
        norm = normalize_evidence(ev)
        assert any(c.startswith("enzyme") or c.startswith("dna_repair") for c in norm.categories)  # reductase→enzyme:redox, polymerase→dna_repair:replication


class TestStringGOTermFormat:
    def test_string_go_term_dict_with_term_key(self):
        """STRING uses {"term": "GO:...", "description": "..."} not {"id": "GO:..."}."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "STRING",
            "go_terms": [
                {"term": "GO:0005524", "description": "ATP binding"},
            ],
        })
        norm = normalize_evidence(ev)
        assert "GO:0005524" in norm.go_terms


class TestStructureOnlyEmpty:
    def test_esmfold_structure_only_empty_norm(self):
        """ESMFold with only structure data should produce minimal normalization."""
        ev = _make_evidence(EvidenceType.STRUCTURE, {
            "source": "ESMFold",
            "avg_plddt": 72.5,
            "pdb_file": "JCVISYN3A_0001.pdb",
        })
        norm = normalize_evidence(ev)
        # No functional terms from pure structure prediction
        assert len(norm.categories) == 0
        assert len(norm.go_terms) == 0
        assert len(norm.ec_numbers) == 0


class TestPairwiseAgreement:
    def test_identical_go_terms(self):
        a = NormalizedEvidence(go_terms={"GO:0005524", "GO:0004386"})
        b = NormalizedEvidence(go_terms={"GO:0005524", "GO:0004386"})
        score = _pairwise_agreement(a, b)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_no_overlap(self):
        a = NormalizedEvidence(
            go_terms={"GO:0005524"},
            categories={"enzyme"},
        )
        b = NormalizedEvidence(
            go_terms={"GO:0005215"},
            categories={"transporter"},
        )
        score = _pairwise_agreement(a, b)
        assert score < 0.1

    def test_same_ec_different_go(self):
        a = NormalizedEvidence(ec_numbers={"2.7.1.1"}, go_terms={"GO:0005524"})
        b = NormalizedEvidence(ec_numbers={"2.7.1.1"}, go_terms={"GO:0016301"})
        score = _pairwise_agreement(a, b)
        # EC match should push score > 0.3
        assert score > 0.3

    def test_same_category_only(self):
        a = NormalizedEvidence(categories={"enzyme"})
        b = NormalizedEvidence(categories={"enzyme"})
        score = _pairwise_agreement(a, b)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_keyword_fallback(self):
        a = NormalizedEvidence(keywords={"helicase", "dna", "repair"})
        b = NormalizedEvidence(keywords={"helicase", "dna", "binding"})
        score = _pairwise_agreement(a, b)
        assert score > 0.0

    def test_partial_ec_match(self):
        a = NormalizedEvidence(ec_numbers={"2.7.1.1"})
        b = NormalizedEvidence(ec_numbers={"2.7.1.2"})
        score = _pairwise_agreement(a, b)
        # Partial match (first 3 fields agree): 2.7.1
        assert score > 0.3


# --- Convergence scoring integration ---

class TestConvergenceScoring:
    def test_agreeing_evidence(self, db):
        """Two pieces of evidence pointing to the same function should score high."""
        from openlab.db.models.gene import Gene

        gene = Gene(
            locus_tag="TEST_0001", sequence="ATGC", length=4,
            strand=1, start=0, end=4, product="hypothetical protein",
        )
        db.add(gene)
        db.flush()

        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "DNA helicase RecQ"}]},
            confidence=0.9,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.STRUCTURE,
            payload={"description": "helicase domain fold"},
            confidence=0.8,
        )
        db.add_all([ev1, ev2])
        db.flush()

        score = compute_convergence_score(db, gene.gene_id)
        assert score > 0.3

    def test_disagreeing_evidence(self, db):
        """Evidence pointing to different functions should score lower."""
        from openlab.db.models.gene import Gene

        gene = Gene(
            locus_tag="TEST_0002", sequence="ATGC", length=4,
            strand=1, start=0, end=4, product="hypothetical protein",
        )
        db.add(gene)
        db.flush()

        ev1 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "ABC transporter permease"}]},
            confidence=0.9,
        )
        ev2 = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.COMPUTATIONAL,
            payload={"predicted_function": "ribosomal protein L10"},
            confidence=0.8,
        )
        db.add_all([ev1, ev2])
        db.flush()

        score = compute_convergence_score(db, gene.gene_id)
        assert score < 0.5

    def test_single_evidence(self, db):
        """A gene with only one evidence record should return 1.0."""
        from openlab.db.models.gene import Gene

        gene = Gene(
            locus_tag="TEST_0003", sequence="ATGC", length=4,
            strand=1, start=0, end=4,
        )
        db.add(gene)
        db.flush()

        ev = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "kinase"}]},
            confidence=0.9,
        )
        db.add(ev)
        db.flush()

        score = compute_convergence_score(db, gene.gene_id)
        assert score == 1.0

    def test_no_evidence(self, db):
        """A gene with no evidence should return 0.0."""
        from openlab.db.models.gene import Gene

        gene = Gene(
            locus_tag="TEST_0004", sequence="ATGC", length=4,
            strand=1, start=0, end=4,
        )
        db.add(gene)
        db.flush()

        score = compute_convergence_score(db, gene.gene_id)
        assert score == 0.0


# --- Pfam domain normalization ---

class TestPfamNormalization:
    def test_pfam_domain_extraction(self):
        """Pfam domains[].description should be extracted and categorized."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "Pfam",
            "database": "Pfam-A",
            "domains": [
                {
                    "name": "PF00005.30",
                    "target_name": "ABC_tran",
                    "description": "ABC transporter",
                    "evalue": 1.2e-15,
                    "score": 52.3,
                },
            ],
        })
        norm = normalize_evidence(ev)
        assert "transporter" in norm.categories or any(
            c.startswith("transporter") for c in norm.categories
        )

    def test_pfam_multiple_domains(self):
        """Multiple Pfam domains should all be extracted."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "Pfam",
            "domains": [
                {"name": "PF00005", "description": "ABC transporter"},
                {"name": "PF00528", "description": "Binding-protein-dependent transport system inner membrane component"},
            ],
        })
        norm = normalize_evidence(ev)
        assert len(norm.keywords) > 0
        assert "transporter" in norm.categories

    def test_pfam_with_ec_in_description(self):
        """EC numbers in Pfam domain descriptions should be extracted."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "Pfam",
            "domains": [
                {"name": "PF00294", "description": "pfkA EC 2.7.1.11 6-phosphofructokinase"},
            ],
        })
        norm = normalize_evidence(ev)
        assert "2.7.1.11" in norm.ec_numbers

    def test_pfam_empty_domains(self):
        """Empty domains list should produce minimal normalization."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "Pfam",
            "domains": [],
        })
        norm = normalize_evidence(ev)
        assert len(norm.categories) == 0


# --- eggNOG normalization ---

class TestEggNOGNormalization:
    def test_eggnnog_go_and_cog(self):
        """eggNOG with GO terms and COG category should be fully extracted."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "eggNOG",
            "go_terms": [
                {"id": "GO:0008168", "description": "methyltransferase activity"},
            ],
            "cog_category": "J",
            "ec_numbers": ["2.1.1.-"],
            "og_description": "SAM-dependent methyltransferase",
        })
        norm = normalize_evidence(ev)
        assert "GO:0008168" in norm.go_terms
        assert "2.1.1.-" in norm.ec_numbers
        assert "translation" in norm.categories  # COG J → translation

    def test_eggnnog_cog_multi_category(self):
        """COG with multiple category letters should map all."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "eggNOG",
            "cog_category": "JK",  # Translation + Transcription
        })
        norm = normalize_evidence(ev)
        assert "translation" in norm.categories
        assert "transcription" in norm.categories

    def test_eggnnog_predicted_name(self):
        """eggNOG predicted_name should contribute to keywords."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "eggNOG",
            "predicted_name": "trmD",
            "og_description": "tRNA methyltransferase",
        })
        norm = normalize_evidence(ev)
        assert len(norm.keywords) > 0

    def test_eggnnog_ec_array(self):
        """eggNOG ec_numbers as array should all be extracted."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "eggNOG",
            "ec_numbers": ["2.1.1.31", "2.7.1.11"],
        })
        norm = normalize_evidence(ev)
        assert "2.1.1.31" in norm.ec_numbers
        assert "2.7.1.11" in norm.ec_numbers

    def test_eggnnog_cog_s_ignored(self):
        """COG S (unknown_function) should not add a useful category."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "eggNOG",
            "cog_category": "S",
        })
        norm = normalize_evidence(ev)
        # S → unknown_function should be excluded from categories
        assert "unknown_function" not in norm.categories

    def test_eggnnog_go_string_format(self):
        """eggNOG GO terms as comma-separated string should be parsed."""
        ev = _make_evidence(EvidenceType.COMPUTATIONAL, {
            "source": "eggNOG",
            "go_terms": [{"id": "GO:0003723"}, {"id": "GO:0005524"}],
        })
        norm = normalize_evidence(ev)
        assert "GO:0003723" in norm.go_terms
        assert "GO:0005524" in norm.go_terms


# --- Foldseek normalization ---

class TestFoldseekNormalization:
    def test_foldseek_hit_description(self):
        """Foldseek hits[].description should be extracted."""
        ev = _make_evidence(EvidenceType.STRUCTURE, {
            "source": "Foldseek",
            "database": "PDB100",
            "hits": [
                {
                    "target": "1abc_A",
                    "description": "DNA helicase RecQ",
                    "fident": 0.35,
                    "evalue": 1e-8,
                    "bits": 120,
                    "tm_score": 0.65,
                },
            ],
        })
        norm = normalize_evidence(ev)
        assert any(
            c.startswith("dna_repair") or c.startswith("enzyme")
            for c in norm.categories
        )

    def test_foldseek_multiple_hits(self):
        """Multiple Foldseek hits should all contribute."""
        ev = _make_evidence(EvidenceType.STRUCTURE, {
            "source": "Foldseek",
            "hits": [
                {"target": "1abc_A", "description": "DNA polymerase III subunit"},
                {"target": "2xyz_B", "description": "ribosomal protein L10"},
            ],
        })
        norm = normalize_evidence(ev)
        assert len(norm.keywords) > 0
        assert len(norm.categories) > 0

    def test_foldseek_no_hits(self):
        """Foldseek with empty hits should produce empty normalization."""
        ev = _make_evidence(EvidenceType.STRUCTURE, {
            "source": "Foldseek",
            "hits": [],
        })
        norm = normalize_evidence(ev)
        assert len(norm.categories) == 0
