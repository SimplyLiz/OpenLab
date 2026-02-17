from openlab.db.models import (
    Evidence,
    EvidenceType,
    Gene,
    Hypothesis,
    HypothesisEvidence,
)
from openlab.db.models.hypothesis import (
    EvidenceDirection,
    HypothesisScope,
    HypothesisStatus,
)


def test_create_hypothesis(db):
    hyp = Hypothesis(
        title="JCVISYN3A_0999 is a membrane transporter",
        description="Based on homology to ABC transporter family",
        scope=HypothesisScope.GENE,
        status=HypothesisStatus.DRAFT,
        confidence_score=0.6,
    )
    db.add(hyp)
    db.flush()

    assert hyp.hypothesis_id is not None
    assert hyp.status == HypothesisStatus.DRAFT


def test_hypothesis_evidence_link(db):
    gene = Gene(
        locus_tag="JCVISYN3A_0050",
        sequence="ATG",
        length=3,
        strand=1,
        start=500,
        end=503,
    )
    db.add(gene)
    db.flush()

    ev = Evidence(
        gene_id=gene.gene_id,
        evidence_type=EvidenceType.HOMOLOGY,
        payload={"hit": "ABC_transporter"},
        confidence=0.8,
    )
    db.add(ev)
    db.flush()

    hyp = Hypothesis(
        title="0050 is ABC transporter",
        scope=HypothesisScope.GENE,
        status=HypothesisStatus.TESTING,
    )
    db.add(hyp)
    db.flush()

    link = HypothesisEvidence(
        hypothesis_id=hyp.hypothesis_id,
        evidence_id=ev.evidence_id,
        direction=EvidenceDirection.SUPPORTS,
        weight=1.0,
    )
    db.add(link)
    db.flush()

    assert len(hyp.evidence_links) == 1
    assert hyp.evidence_links[0].direction == EvidenceDirection.SUPPORTS
