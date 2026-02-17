"""Evidence API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from openlab.api.deps import get_db
from openlab.api.v1.schemas import EvidenceCreate, EvidenceCreated
from openlab.services import evidence_service

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("", response_model=EvidenceCreated)
def add_evidence(
    body: EvidenceCreate,
    db: Session = Depends(get_db),
):
    """Add a piece of evidence for a gene."""
    ev = evidence_service.add_evidence(
        db=db,
        gene_id=body.gene_id,
        evidence_type=body.evidence_type,
        payload=body.payload,
        source_ref=body.source_ref,
        confidence=body.confidence,
        quality_score=body.quality_score,
        notes=body.notes,
    )
    return ev
