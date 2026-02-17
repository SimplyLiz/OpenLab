"""Tests for gene service freshness helpers."""

from datetime import datetime, timedelta

from openlab.db.models import Evidence, EvidenceType, Gene
from openlab.services import gene_service


def _make_gene(db, locus="JCVISYN3A_0200", product="hypothetical protein"):
    gene = Gene(
        locus_tag=locus,
        sequence="ATG",
        protein_sequence="M",
        length=3,
        strand=1,
        start=1000,
        end=1003,
        product=product,
    )
    db.add(gene)
    db.flush()
    return gene


def _make_evidence(db, gene_id, etype=EvidenceType.HOMOLOGY, confidence=0.8):
    ev = Evidence(
        gene_id=gene_id,
        evidence_type=etype,
        payload={"source": "test"},
        confidence=confidence,
    )
    db.add(ev)
    db.flush()
    return ev


def test_has_recent_evidence_true(db):
    gene = _make_gene(db, "JCVISYN3A_FR01")
    _make_evidence(db, gene.gene_id)
    db.commit()

    assert gene_service.has_recent_evidence(db, gene.gene_id, EvidenceType.HOMOLOGY, 30)


def test_has_recent_evidence_false_no_evidence(db):
    gene = _make_gene(db, "JCVISYN3A_FR02")
    db.commit()

    assert not gene_service.has_recent_evidence(db, gene.gene_id, EvidenceType.HOMOLOGY, 30)


def test_has_recent_evidence_false_wrong_type(db):
    gene = _make_gene(db, "JCVISYN3A_FR03")
    _make_evidence(db, gene.gene_id, etype=EvidenceType.STRUCTURE)
    db.commit()

    assert not gene_service.has_recent_evidence(db, gene.gene_id, EvidenceType.HOMOLOGY, 30)


def test_genes_without_evidence(db):
    # Gene with evidence
    gene1 = _make_gene(db, "JCVISYN3A_FR04")
    _make_evidence(db, gene1.gene_id)

    # Gene without evidence
    gene2 = _make_gene(db, "JCVISYN3A_FR05")

    # Gene with known function (should be excluded)
    gene3 = _make_gene(db, "JCVISYN3A_FR06", product="DNA polymerase")

    db.commit()

    results = gene_service.genes_without_evidence(db)
    loci = [g.locus_tag for g in results]
    assert "JCVISYN3A_FR05" in loci
    assert "JCVISYN3A_FR04" not in loci
    assert "JCVISYN3A_FR06" not in loci


def test_genes_with_stale_evidence(db):
    # Gene with fresh evidence — should NOT appear
    gene1 = _make_gene(db, "JCVISYN3A_FR07")
    _make_evidence(db, gene1.gene_id)

    db.commit()

    # Fresh evidence: should be empty for the genes we just created
    stale = gene_service.genes_with_stale_evidence(db, max_age_days=30)
    loci = [g.locus_tag for g in stale]
    assert "JCVISYN3A_FR07" not in loci
