import json

from openlab.db.models import Evidence, EvidenceType, Gene


def test_create_evidence(db):
    gene = Gene(
        locus_tag="JCVISYN3A_0010",
        sequence="ATGAAA",
        length=6,
        strand=1,
        start=100,
        end=106,
    )
    db.add(gene)
    db.flush()

    ev = Evidence(
        gene_id=gene.gene_id,
        evidence_type=EvidenceType.HOMOLOGY,
        payload={"blast_hit": "UniRef90_Q9X0A1", "evalue": 1e-50},
        source_ref="BLAST vs UniRef90",
        confidence=0.95,
        quality_score=0.9,
    )
    db.add(ev)
    db.flush()

    assert ev.evidence_id is not None
    assert ev.evidence_type == EvidenceType.HOMOLOGY
    assert ev.payload["evalue"] == 1e-50
    assert ev.gene.locus_tag == "JCVISYN3A_0010"


def test_evidence_type_enum():
    assert EvidenceType.HOMOLOGY.value == "HOMOLOGY"
    assert EvidenceType.GROWTH_CURVE.value == "GROWTH_CURVE"
    members = [e.value for e in EvidenceType]
    assert "STRUCTURE" in members
    assert "EXPRESSION" in members
