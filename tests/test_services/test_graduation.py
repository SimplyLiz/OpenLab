"""Tests for gene graduation service functions."""

import pytest

from openlab.exceptions import GeneNotFoundError, HypothesisNotFoundError
from openlab.db.models.gene import Gene
from openlab.db.models.hypothesis import Hypothesis, HypothesisScope, HypothesisStatus
from openlab.services import gene_service


def _make_gene(db, locus_tag, product="hypothetical protein", **kw):
    gene = Gene(
        locus_tag=locus_tag,
        sequence="ATGC" * 25,
        protein_sequence="M" * 30,
        length=100,
        strand=1,
        start=kw.get("start", 1),
        end=kw.get("end", 100),
        product=product,
    )
    db.add(gene)
    db.flush()
    return gene


def _make_hypothesis(db, gene, title="Test hypothesis", confidence=0.8):
    hyp = Hypothesis(
        title=title,
        description="A test hypothesis",
        scope=HypothesisScope.GENE,
        status=HypothesisStatus.DRAFT,
        confidence_score=confidence,
        gene_id=gene.gene_id,
    )
    db.add(hyp)
    db.flush()
    return hyp


class TestGraduateGene:
    def test_graduate_with_hypothesis(self, db):
        gene = _make_gene(db, "JCVISYN3A_9001")
        hyp = _make_hypothesis(db, gene)

        result = gene_service.graduate_gene(
            db, gene.gene_id, "membrane transporter", hypothesis_id=hyp.hypothesis_id
        )
        assert result.proposed_function == "membrane transporter"
        assert result.graduated_at is not None
        assert result.graduation_hypothesis_id == hyp.hypothesis_id

    def test_graduate_without_hypothesis(self, db):
        gene = _make_gene(db, "JCVISYN3A_9002")

        result = gene_service.graduate_gene(
            db, gene.gene_id, "manual annotation: lipase"
        )
        assert result.proposed_function == "manual annotation: lipase"
        assert result.graduated_at is not None
        assert result.graduation_hypothesis_id is None

    def test_graduate_invalid_hypothesis(self, db):
        gene = _make_gene(db, "JCVISYN3A_9003")

        with pytest.raises(HypothesisNotFoundError):
            gene_service.graduate_gene(
                db, gene.gene_id, "something", hypothesis_id=99999
            )

    def test_graduate_excludes_from_unknown_filter(self, db):
        gene = _make_gene(db, "JCVISYN3A_9004")

        # Before graduation: shows up in unknown list
        unknown_before = gene_service.list_genes(db, unknown_only=True, limit=5000)
        tags_before = [g.locus_tag for g in unknown_before]
        assert "JCVISYN3A_9004" in tags_before

        gene_service.graduate_gene(db, gene.gene_id, "ATPase")

        # After graduation: no longer in unknown list
        unknown_after = gene_service.list_genes(db, unknown_only=True, limit=5000)
        tags_after = [g.locus_tag for g in unknown_after]
        assert "JCVISYN3A_9004" not in tags_after


class TestUngraduateGene:
    def test_ungraduate(self, db):
        gene = _make_gene(db, "JCVISYN3A_9010")
        hyp = _make_hypothesis(db, gene)
        gene_service.graduate_gene(
            db, gene.gene_id, "kinase", hypothesis_id=hyp.hypothesis_id
        )

        result = gene_service.ungraduate_gene(db, gene.gene_id)
        assert result.proposed_function is None
        assert result.graduated_at is None
        assert result.graduation_hypothesis_id is None

    def test_ungraduate_returns_to_unknown(self, db):
        gene = _make_gene(db, "JCVISYN3A_9011")
        gene_service.graduate_gene(db, gene.gene_id, "helicase")

        # Graduated → not unknown
        unknown = gene_service.list_genes(db, unknown_only=True, limit=5000)
        assert gene.locus_tag not in [g.locus_tag for g in unknown]

        gene_service.ungraduate_gene(db, gene.gene_id)

        # Un-graduated → unknown again
        unknown = gene_service.list_genes(db, unknown_only=True, limit=5000)
        assert gene.locus_tag in [g.locus_tag for g in unknown]

    def test_ungraduate_not_graduated(self, db):
        gene = _make_gene(db, "JCVISYN3A_9012")

        with pytest.raises(ValueError, match="not graduated"):
            gene_service.ungraduate_gene(db, gene.gene_id)


class TestListCandidates:
    def test_list_graduation_candidates(self, db):
        gene = _make_gene(db, "JCVISYN3A_9020")
        _make_hypothesis(db, gene, confidence=0.85)

        candidates = gene_service.list_graduation_candidates(db, min_confidence=0.7)
        tags = [c["locus_tag"] for c in candidates]
        assert "JCVISYN3A_9020" in tags

    def test_candidates_excludes_graduated(self, db):
        gene = _make_gene(db, "JCVISYN3A_9021")
        hyp = _make_hypothesis(db, gene, confidence=0.9)
        gene_service.graduate_gene(
            db, gene.gene_id, "graduated already", hypothesis_id=hyp.hypothesis_id
        )

        candidates = gene_service.list_graduation_candidates(db, min_confidence=0.7)
        tags = [c["locus_tag"] for c in candidates]
        assert "JCVISYN3A_9021" not in tags

    def test_candidates_excludes_low_confidence(self, db):
        gene = _make_gene(db, "JCVISYN3A_9022")
        _make_hypothesis(db, gene, confidence=0.3)

        candidates = gene_service.list_graduation_candidates(db, min_confidence=0.7)
        tags = [c["locus_tag"] for c in candidates]
        assert "JCVISYN3A_9022" not in tags


class TestListGraduated:
    def test_list_graduated_genes(self, db):
        gene = _make_gene(db, "JCVISYN3A_9030")
        gene_service.graduate_gene(db, gene.gene_id, "protease")

        graduated = gene_service.list_graduated_genes(db)
        tags = [g.locus_tag for g in graduated]
        assert "JCVISYN3A_9030" in tags
