"""Hypothesis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from openlab.api.deps import get_db
from openlab.api.v1.schemas import (
    EvidenceLinkCreate,
    HypothesisCreate,
    HypothesisDetail,
    HypothesisEvidenceLinkOut,
    HypothesisListItem,
    HypothesisUpdate,
    ScoreOut,
)
from openlab.exceptions import HypothesisNotFoundError
from openlab.db.models.hypothesis import HypothesisStatus
from openlab.services import hypothesis_service

router = APIRouter(prefix="/hypotheses", tags=["hypotheses"])


@router.get("", response_model=list[HypothesisListItem])
def list_hypotheses(
    gene_id: int | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List all hypotheses, optionally filtered by gene_id."""
    return hypothesis_service.list_hypotheses(
        db, gene_id=gene_id, limit=limit, offset=offset
    )


@router.post("", response_model=HypothesisDetail, status_code=201)
def create_hypothesis(
    body: HypothesisCreate,
    db: Session = Depends(get_db),
):
    """Create a new hypothesis."""
    hyp = hypothesis_service.create_hypothesis(
        db=db,
        title=body.title,
        description=body.description or "",
        confidence_score=0.0,
        evidence_ids=[],
        scope=body.scope,
        gene_id=body.gene_id,
    )
    return hypothesis_service.get_hypothesis(db, hyp.hypothesis_id)


@router.get("/{hypothesis_id}", response_model=HypothesisDetail)
def get_hypothesis(hypothesis_id: int, db: Session = Depends(get_db)):
    """Get a hypothesis by ID with linked evidence."""
    hyp = hypothesis_service.get_hypothesis(db, hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return hyp


@router.patch("/{hypothesis_id}", response_model=HypothesisDetail)
def update_hypothesis(
    hypothesis_id: int,
    body: HypothesisUpdate,
    db: Session = Depends(get_db),
):
    """Update a hypothesis."""
    try:
        hypothesis_service.update_hypothesis(
            db,
            hypothesis_id,
            title=body.title,
            description=body.description,
            status=body.status,
        )
    except HypothesisNotFoundError:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return hypothesis_service.get_hypothesis(db, hypothesis_id)


@router.delete("/{hypothesis_id}", status_code=204)
def delete_hypothesis(hypothesis_id: int, db: Session = Depends(get_db)):
    """Delete a hypothesis."""
    try:
        hypothesis_service.delete_hypothesis(db, hypothesis_id)
    except HypothesisNotFoundError:
        raise HTTPException(status_code=404, detail="Hypothesis not found")


@router.post(
    "/{hypothesis_id}/evidence",
    response_model=HypothesisEvidenceLinkOut,
    status_code=201,
)
def link_evidence(
    hypothesis_id: int,
    body: EvidenceLinkCreate,
    db: Session = Depends(get_db),
):
    """Link evidence to a hypothesis."""
    try:
        link = hypothesis_service.link_evidence(
            db,
            hypothesis_id=hypothesis_id,
            evidence_id=body.evidence_id,
            direction=body.direction,
            weight=body.weight,
        )
    except HypothesisNotFoundError:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return link


@router.delete("/{hypothesis_id}/evidence/{evidence_id}", status_code=204)
def unlink_evidence(
    hypothesis_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """Remove an evidence link from a hypothesis."""
    try:
        hypothesis_service.unlink_evidence(db, hypothesis_id, evidence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{hypothesis_id}/score", response_model=ScoreOut)
def compute_score(hypothesis_id: int, db: Session = Depends(get_db)):
    """Recompute confidence score from linked evidence."""
    try:
        score = hypothesis_service.compute_score(db, hypothesis_id)
    except HypothesisNotFoundError:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return ScoreOut(hypothesis_id=hypothesis_id, confidence_score=score)
