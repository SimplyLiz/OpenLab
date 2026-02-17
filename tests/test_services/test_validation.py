"""Tests for validation service."""

from datetime import UTC, datetime
from unittest.mock import patch, MagicMock

import pytest

from openlab.db.models import Evidence, EvidenceType, Gene, Hypothesis
from openlab.db.models.hypothesis import HypothesisScope, HypothesisStatus
from openlab.services.validation_service import (
    _compare_functions,
    _extract_predicted_function,
    bootstrap_stability,
    compute_all_convergence,
    consistency_validation,
    leave_one_out,
    ortholog_validation,
    validate_all,
)
from openlab.services.gene_service import compute_convergence_score


@pytest.fixture
def validation_gene(db):
    """Gene with curated reclassification + other evidence."""
    gene = Gene(
        locus_tag="JCVISYN3A_0100",
        sequence="ATGAAA",
        protein_sequence="MAAAAAAA",
        length=6,
        strand=1,
        start=10000,
        end=10006,
        product="hypothetical protein",
    )
    db.add(gene)
    db.flush()

    # Curated reclassification evidence
    ev_curated = Evidence(
        gene_id=gene.gene_id,
        evidence_type=EvidenceType.LITERATURE,
        payload={
            "source": "CuratedReclassification",
            "predicted_function": "DNA methyltransferase",
            "paper_source": "Bianchi 2022",
        },
        source_ref=f"CuratedReclassification:{gene.locus_tag}",
        confidence=0.9,
    )
    # BLAST evidence
    ev_blast = Evidence(
        gene_id=gene.gene_id,
        evidence_type=EvidenceType.HOMOLOGY,
        payload={
            "source": "NCBI_BLAST",
            "hits": [{"description": "DNA methyltransferase domain", "evalue": 1e-20}],
        },
        source_ref="BLAST:RID:TEST",
        confidence=0.8,
    )
    db.add_all([ev_curated, ev_blast])
    db.flush()
    return db, gene


class TestCompareFunctions:
    def test_exact_match(self):
        score = _compare_functions("DNA methyltransferase", "DNA methyltransferase")
        assert score == 1.0

    def test_partial_match(self):
        score = _compare_functions(
            "DNA methyltransferase",
            "methyltransferase domain protein"
        )
        assert 0.0 < score < 1.0

    def test_no_match(self):
        score = _compare_functions(
            "DNA methyltransferase",
            "membrane lipid transporter"
        )
        assert score == 0.0

    def test_empty_strings(self):
        assert _compare_functions("", "something") == 0.0
        assert _compare_functions("something", "") == 0.0


class TestExtractPredictedFunction:
    def test_extracts_predicted_function(self):
        response = "Predicted function: DNA methyltransferase\nConfidence: 0.8"
        assert "DNA methyltransferase" in _extract_predicted_function(response)

    def test_extracts_numbered_list(self):
        response = "1. This gene likely encodes a helicase\n2. Confidence: 0.6"
        result = _extract_predicted_function(response)
        assert "helicase" in result

    def test_fallback_first_line(self):
        response = "The protein is a membrane transporter"
        result = _extract_predicted_function(response)
        assert "membrane transporter" in result


class TestLeaveOneOut:
    def test_loo_with_matching_prediction(self, validation_gene):
        db, gene = validation_gene

        mock_response = (
            "Predicted function: DNA methyltransferase\n"
            "Confidence: 0.75\n"
            "The BLAST evidence clearly shows homology to methyltransferases."
        )

        with patch("openlab.services.validation_service.llm_service") as mock_llm:
            mock_llm.synthesize.return_value = mock_response
            results = leave_one_out(db)

        assert len(results) == 1
        r = results[0]
        assert r["locus_tag"] == "JCVISYN3A_0100"
        assert r["curated_function"] == "DNA methyltransferase"
        assert r["match_score"] > 0.0
        assert r["passed"] is True

    def test_loo_gene_filter(self, validation_gene):
        db, gene = validation_gene

        with patch("openlab.services.validation_service.llm_service") as mock_llm:
            mock_llm.synthesize.return_value = "Predicted function: unknown\nConfidence: 0.3"
            # Pass non-existent gene_id — should return empty
            results = leave_one_out(db, gene_ids=[99999])

        assert len(results) == 0


class TestComputeAllConvergence:
    def test_computes_for_all_hypotheses(self, validation_gene):
        db, gene = validation_gene

        hyp = Hypothesis(
            title="Test hypothesis",
            description="Testing convergence",
            scope=HypothesisScope.GENE,
            status=HypothesisStatus.DRAFT,
            confidence_score=0.7,
            gene_id=gene.gene_id,
        )
        db.add(hyp)
        db.flush()

        results = compute_all_convergence(db)

        assert len(results) == 1
        r = results[0]
        assert r["gene_id"] == gene.gene_id
        assert r["locus_tag"] == "JCVISYN3A_0100"
        assert 0.0 <= r["convergence_score"] <= 1.0

        # Verify hypothesis was updated
        db.refresh(hyp)
        assert hyp.convergence_score is not None


@pytest.fixture
def graduated_gene(db):
    """A graduated gene with evidence and proposed function."""
    gene = Gene(
        locus_tag="JCVISYN3A_0100",
        sequence="ATGAAA",
        protein_sequence="MAAAAAAA",
        length=6,
        strand=1,
        start=10000,
        end=10006,
        product="hypothetical protein",
        proposed_function="DNA methyltransferase",
        graduated_at=datetime.now(UTC),
    )
    db.add(gene)
    db.flush()

    ev = Evidence(
        gene_id=gene.gene_id,
        evidence_type=EvidenceType.HOMOLOGY,
        payload={"hits": [{"description": "DNA methyltransferase domain"}]},
        confidence=0.8,
    )
    db.add(ev)
    db.flush()
    return db, gene


class TestOrthologValidation:
    def test_matches_known_function(self, graduated_gene, tmp_path):
        """Ortholog with matching function should pass."""
        db, gene = graduated_gene

        orthologs = tmp_path / "orthologs.yaml"
        orthologs.write_text(
            f"{gene.locus_tag}:\n"
            f"  ortholog_gene: MG_023\n"
            f"  ortholog_function: DNA methyltransferase\n"
            f"  source: UniProt:P47275\n"
            f"  identity_pct: 55.2\n"
        )

        results = ortholog_validation(db, ortholog_path=str(orthologs))
        assert len(results) == 1
        assert results[0]["passed"] is True
        assert results[0]["match_score"] > 0.0

    def test_mismatched_function(self, graduated_gene, tmp_path):
        """Ortholog with different function should fail."""
        db, gene = graduated_gene

        orthologs = tmp_path / "orthologs.yaml"
        orthologs.write_text(
            f"{gene.locus_tag}:\n"
            f"  ortholog_gene: MG_023\n"
            f"  ortholog_function: ribosomal protein S12\n"
            f"  source: UniProt:P47275\n"
            f"  identity_pct: 55.2\n"
        )

        results = ortholog_validation(db, ortholog_path=str(orthologs))
        assert len(results) == 1
        assert results[0]["passed"] is False


class TestConsistencyValidation:
    def test_consistent_gene(self, graduated_gene):
        """Gene with matching evidence and proposed function is consistent."""
        db, gene = graduated_gene
        results = consistency_validation(db)
        assert len(results) >= 1
        r = [x for x in results if x["gene_id"] == gene.gene_id]
        if r:
            assert r[0]["consistent"] is True


class TestBootstrapStability:
    def test_stable_with_agreeing_evidence(self, db):
        """Evidence all pointing same direction should be stable."""
        gene = Gene(
            locus_tag="BOOT_0001",
            sequence="ATGAAA",
            protein_sequence="MAAAA",
            length=6,
            strand=1,
            start=0,
            end=6,
        )
        db.add(gene)
        db.flush()

        # Add 5 agreeing evidence records
        for i in range(5):
            ev = Evidence(
                gene_id=gene.gene_id,
                evidence_type=EvidenceType.HOMOLOGY,
                payload={"hits": [{"description": f"DNA polymerase variant {i}"}]},
                confidence=0.8,
            )
            db.add(ev)
        db.flush()

        result = bootstrap_stability(db, gene.gene_id, n_iterations=20)
        assert result["stable"] is True
        assert result["std"] < 0.15
        assert result["n_evidence"] == 5

    def test_few_evidence_returns_base(self, db):
        """With < 3 evidence records, no bootstrap is run."""
        gene = Gene(
            locus_tag="BOOT_0002",
            sequence="ATGAAA",
            protein_sequence="MAAAA",
            length=6,
            strand=1,
            start=0,
            end=6,
        )
        db.add(gene)
        db.flush()

        ev = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.HOMOLOGY,
            payload={"hits": [{"description": "kinase"}]},
            confidence=0.8,
        )
        db.add(ev)
        db.flush()

        result = bootstrap_stability(db, gene.gene_id)
        assert result["n_iterations"] == 0
        assert result["stable"] is True


class TestValidateAll:
    def test_combined_report(self, graduated_gene, tmp_path):
        """validate_all should produce a report with all sections."""
        db, gene = graduated_gene

        orthologs = tmp_path / "orthologs.yaml"
        orthologs.write_text(
            f"{gene.locus_tag}:\n"
            f"  ortholog_gene: MG_023\n"
            f"  ortholog_function: DNA methyltransferase\n"
            f"  source: UniProt:P47275\n"
            f"  identity_pct: 55.2\n"
        )

        report = validate_all(db, ortholog_path=str(orthologs))
        assert "ortholog" in report
        assert "consistency" in report
        assert "summary" in report
        assert 0.0 <= report["summary"]["ortholog_accuracy"] <= 1.0
        assert 0.0 <= report["summary"]["consistency_rate"] <= 1.0
        assert "estimated_fpr" in report["summary"]
