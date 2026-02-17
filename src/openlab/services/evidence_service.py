"""Evidence service -- shared logic for CLI and API."""

from sqlalchemy.orm import Session

from openlab.exceptions import GeneNotFoundError
from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.db.models.gene import Gene


def add_evidence(
    db: Session,
    gene_id: int,
    evidence_type: EvidenceType,
    payload: dict,
    source_ref: str | None = None,
    confidence: float | None = None,
    quality_score: float | None = None,
    notes: str | None = None,
) -> Evidence:
    """Add a piece of evidence for a gene."""
    gene = db.query(Gene).filter(Gene.gene_id == gene_id).first()
    if not gene:
        raise GeneNotFoundError(f"Gene {gene_id} not found")

    ev = Evidence(
        gene_id=gene_id,
        evidence_type=evidence_type,
        payload=payload,
        source_ref=source_ref,
        confidence=confidence,
        quality_score=quality_score,
        notes=notes,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def list_evidence(
    db: Session,
    gene_id: int | None = None,
    evidence_type: EvidenceType | None = None,
) -> list[Evidence]:
    """List evidence, optionally filtered by gene and/or type."""
    q = db.query(Evidence)
    if gene_id is not None:
        q = q.filter(Evidence.gene_id == gene_id)
    if evidence_type is not None:
        q = q.filter(Evidence.evidence_type == evidence_type)
    return q.order_by(Evidence.evidence_id).all()
