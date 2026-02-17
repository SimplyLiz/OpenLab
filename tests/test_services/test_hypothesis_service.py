"""Tests for hypothesis service."""

import pytest

from openlab.exceptions import HypothesisNotFoundError
from openlab.db.models import Evidence, EvidenceType, Gene, Hypothesis
from openlab.db.models.hypothesis import (
    EvidenceDirection,
    HypothesisScope,
    HypothesisStatus,
)
from openlab.services import hypothesis_service


def _make_gene(db, locus="JCVISYN3A_0100"):
    gene = Gene(
        locus_tag=locus, sequence="ATG", length=3, strand=1, start=1000, end=1003
    )
    db.add(gene)
    db.flush()
    return gene


def _make_evidence(db, gene_id, etype=EvidenceType.HOMOLOGY, confidence=0.8):
    ev = Evidence(
        gene_id=gene_id,
        evidence_type=etype,
        payload={"source": "BLAST", "hits": [{"accession": "P12345"}]},
        confidence=confidence,
    )
    db.add(ev)
    db.flush()
    return ev


def test_create_hypothesis(db):
    gene = _make_gene(db)
    ev = _make_evidence(db, gene.gene_id)

    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Test function prediction",
        description="Based on BLAST homology",
        confidence_score=0.75,
        evidence_ids=[ev.evidence_id],
    )

    assert hyp.hypothesis_id is not None
    assert hyp.title == "Test function prediction"
    assert hyp.confidence_score == 0.75
    assert hyp.scope == HypothesisScope.GENE
    assert hyp.status == HypothesisStatus.DRAFT
    assert len(hyp.evidence_links) == 1


def test_create_hypothesis_with_gene_id(db):
    gene = _make_gene(db, locus="JCVISYN3A_0110")
    ev = _make_evidence(db, gene.gene_id)

    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Gene-linked hypothesis",
        description="Test gene FK",
        confidence_score=0.8,
        evidence_ids=[ev.evidence_id],
        gene_id=gene.gene_id,
    )

    assert hyp.gene_id == gene.gene_id


def test_list_hypotheses(db):
    gene = _make_gene(db, locus="JCVISYN3A_0101")
    ev = _make_evidence(db, gene.gene_id)
    hypothesis_service.create_hypothesis(
        db=db,
        title="Hypothesis A",
        description="Desc A",
        confidence_score=0.5,
        evidence_ids=[ev.evidence_id],
    )

    results = hypothesis_service.list_hypotheses(db)
    assert len(results) >= 1
    assert any(h.title == "Hypothesis A" for h in results)


def test_list_hypotheses_filter_gene_id(db):
    gene = _make_gene(db, locus="JCVISYN3A_0111")
    ev = _make_evidence(db, gene.gene_id)
    hypothesis_service.create_hypothesis(
        db=db,
        title="Filtered by gene",
        description="Test",
        confidence_score=0.5,
        evidence_ids=[ev.evidence_id],
        gene_id=gene.gene_id,
    )

    results = hypothesis_service.list_hypotheses(db, gene_id=gene.gene_id)
    assert len(results) == 1
    assert results[0].title == "Filtered by gene"


def test_get_hypothesis(db):
    gene = _make_gene(db, locus="JCVISYN3A_0102")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Fetch test",
        description="For get_hypothesis test",
        confidence_score=0.6,
        evidence_ids=[ev.evidence_id],
    )

    fetched = hypothesis_service.get_hypothesis(db, hyp.hypothesis_id)
    assert fetched is not None
    assert fetched.title == "Fetch test"
    assert len(fetched.evidence_links) == 1


def test_get_hypothesis_for_gene(db):
    gene = _make_gene(db, locus="JCVISYN3A_0103")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Gene-linked hypothesis",
        description="Test gene link",
        confidence_score=0.9,
        evidence_ids=[ev.evidence_id],
        gene_id=gene.gene_id,
    )

    result = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
    assert result is not None
    assert result.hypothesis_id == hyp.hypothesis_id


def test_get_hypothesis_for_gene_fallback(db):
    """Fallback via evidence-link join when gene_id is not set."""
    gene = _make_gene(db, locus="JCVISYN3A_0104")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Legacy hypothesis",
        description="No gene_id set",
        confidence_score=0.7,
        evidence_ids=[ev.evidence_id],
        # gene_id intentionally omitted
    )

    result = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
    assert result is not None
    assert result.hypothesis_id == hyp.hypothesis_id


def test_get_hypothesis_for_gene_no_match(db):
    result = hypothesis_service.get_hypothesis_for_gene(db, 99999)
    assert result is None


def test_update_hypothesis(db):
    gene = _make_gene(db, locus="JCVISYN3A_0105")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Original",
        description="Original desc",
        confidence_score=0.5,
        evidence_ids=[ev.evidence_id],
    )

    updated = hypothesis_service.update_hypothesis(
        db, hyp.hypothesis_id,
        title="Updated",
        status=HypothesisStatus.TESTING,
    )
    assert updated.title == "Updated"
    assert updated.status == HypothesisStatus.TESTING


def test_update_hypothesis_not_found(db):
    with pytest.raises(HypothesisNotFoundError):
        hypothesis_service.update_hypothesis(db, 99999, title="Nope")


def test_delete_hypothesis(db):
    gene = _make_gene(db, locus="JCVISYN3A_0106")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="To delete",
        description="Delete me",
        confidence_score=0.5,
        evidence_ids=[ev.evidence_id],
    )
    hid = hyp.hypothesis_id

    hypothesis_service.delete_hypothesis(db, hid)
    assert hypothesis_service.get_hypothesis(db, hid) is None


def test_delete_hypothesis_not_found(db):
    with pytest.raises(HypothesisNotFoundError):
        hypothesis_service.delete_hypothesis(db, 99999)


def test_link_evidence(db):
    gene = _make_gene(db, locus="JCVISYN3A_0107")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Link test",
        description="Test",
        confidence_score=0.5,
        evidence_ids=[],
    )

    link = hypothesis_service.link_evidence(
        db, hyp.hypothesis_id, ev.evidence_id,
        direction=EvidenceDirection.SUPPORTS,
        weight=2.0,
    )
    assert link.evidence_id == ev.evidence_id
    assert link.weight == 2.0


def test_link_evidence_updates_existing(db):
    gene = _make_gene(db, locus="JCVISYN3A_0108")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Relink test",
        description="Test",
        confidence_score=0.5,
        evidence_ids=[ev.evidence_id],
    )

    # Re-link with different direction
    link = hypothesis_service.link_evidence(
        db, hyp.hypothesis_id, ev.evidence_id,
        direction=EvidenceDirection.CONTRADICTS,
        weight=3.0,
    )
    assert link.direction == EvidenceDirection.CONTRADICTS
    assert link.weight == 3.0


def test_unlink_evidence(db):
    gene = _make_gene(db, locus="JCVISYN3A_0109")
    ev = _make_evidence(db, gene.gene_id)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Unlink test",
        description="Test",
        confidence_score=0.5,
        evidence_ids=[ev.evidence_id],
    )

    hypothesis_service.unlink_evidence(db, hyp.hypothesis_id, ev.evidence_id)

    fetched = hypothesis_service.get_hypothesis(db, hyp.hypothesis_id)
    assert len(fetched.evidence_links) == 0


def test_unlink_evidence_not_found(db):
    gene = _make_gene(db, locus="JCVISYN3A_0112")
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Bad unlink",
        description="Test",
        confidence_score=0.5,
        evidence_ids=[],
    )

    with pytest.raises(ValueError, match="No link"):
        hypothesis_service.unlink_evidence(db, hyp.hypothesis_id, 99999)


def test_compute_score_supports(db):
    gene = _make_gene(db, locus="JCVISYN3A_0113")
    ev = _make_evidence(db, gene.gene_id, etype=EvidenceType.HOMOLOGY, confidence=0.8)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Score test",
        description="Test scoring",
        confidence_score=0.0,
        evidence_ids=[ev.evidence_id],
    )

    score = hypothesis_service.compute_score(db, hyp.hypothesis_id)
    # HOMOLOGY type_weight=1.0, direction=SUPPORTS(+1), weight=1.0, confidence=0.8
    # score = (1.0 * 1.0 * 0.8 * 1.0) / (1.0 * 1.0) = 0.8
    assert score == pytest.approx(0.8)


def test_compute_score_mixed_evidence(db):
    gene = _make_gene(db, locus="JCVISYN3A_0114")
    ev1 = _make_evidence(db, gene.gene_id, etype=EvidenceType.TRANSPOSON, confidence=0.95)
    ev2 = _make_evidence(db, gene.gene_id, etype=EvidenceType.HOMOLOGY, confidence=0.8)
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Mixed score",
        description="Test",
        confidence_score=0.0,
        evidence_ids=[ev1.evidence_id],
    )
    # Add second with CONTRADICTS
    hypothesis_service.link_evidence(
        db, hyp.hypothesis_id, ev2.evidence_id,
        direction=EvidenceDirection.CONTRADICTS,
    )

    score = hypothesis_service.compute_score(db, hyp.hypothesis_id)
    # TRANSPOSON: +1 * 1.0 * 0.95 * 2.0 = 1.9, denom: 1.0 * 2.0 = 2.0
    # HOMOLOGY: -1 * 1.0 * 0.8 * 1.0 = -0.8, denom: 1.0 * 1.0 = 1.0
    # total = (1.9 - 0.8) / (2.0 + 1.0) = 1.1 / 3.0 ≈ 0.3667
    assert 0.3 < score < 0.4


def test_compute_score_no_evidence(db):
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title="Empty score",
        description="No evidence",
        confidence_score=0.0,
        evidence_ids=[],
    )
    score = hypothesis_service.compute_score(db, hyp.hypothesis_id)
    assert score == 0.0


def test_compute_score_not_found(db):
    with pytest.raises(HypothesisNotFoundError):
        hypothesis_service.compute_score(db, 99999)
