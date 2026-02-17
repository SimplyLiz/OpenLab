"""Hypothesis service — create and manage hypotheses."""

from sqlalchemy.orm import Session, joinedload

from openlab.exceptions import HypothesisNotFoundError
from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.db.models.hypothesis import (
    EvidenceDirection,
    Hypothesis,
    HypothesisEvidence,
    HypothesisScope,
    HypothesisStatus,
)

# Weights by evidence type for scoring
TYPE_WEIGHTS = {
    "TRANSPOSON": 2.0,
    "GROWTH_CURVE": 1.8,
    "SIMULATION": 1.6,
    "STRUCTURE": 1.5,
    "LITERATURE": 1.5,
    "PROTEOMICS": 1.3,
    "EXPRESSION": 1.2,
    "HOMOLOGY": 1.0,
    "COMPUTATIONAL": 0.8,
}

DIRECTION_FACTOR = {
    "SUPPORTS": +1.0,
    "CONTRADICTS": -1.0,
    "NEUTRAL": 0.0,
}


def create_hypothesis(
    db: Session,
    title: str,
    description: str,
    confidence_score: float,
    evidence_ids: list[int],
    scope: HypothesisScope = HypothesisScope.GENE,
    status: HypothesisStatus = HypothesisStatus.DRAFT,
    gene_id: int | None = None,
) -> Hypothesis:
    """Create a hypothesis linked to evidence records."""
    hyp = Hypothesis(
        title=title,
        description=description,
        scope=scope,
        status=status,
        confidence_score=confidence_score,
        gene_id=gene_id,
    )
    db.add(hyp)
    db.flush()

    for eid in evidence_ids:
        link = HypothesisEvidence(
            hypothesis_id=hyp.hypothesis_id,
            evidence_id=eid,
            direction=EvidenceDirection.SUPPORTS,
            weight=1.0,
        )
        db.add(link)

    db.commit()
    db.refresh(hyp)
    return hyp


def update_hypothesis(
    db: Session,
    hypothesis_id: int,
    **kwargs,
) -> Hypothesis:
    """Update hypothesis fields. Accepts title, description, status."""
    hyp = _get_or_raise(db, hypothesis_id)

    allowed = {"title", "description", "status"}
    for key, value in kwargs.items():
        if key in allowed and value is not None:
            setattr(hyp, key, value)

    db.commit()
    db.refresh(hyp)
    return hyp


def delete_hypothesis(db: Session, hypothesis_id: int) -> None:
    """Delete a hypothesis and its evidence links."""
    hyp = _get_or_raise(db, hypothesis_id)
    db.delete(hyp)
    db.commit()


def link_evidence(
    db: Session,
    hypothesis_id: int,
    evidence_id: int,
    direction: EvidenceDirection = EvidenceDirection.SUPPORTS,
    weight: float = 1.0,
) -> HypothesisEvidence:
    """Link an evidence record to a hypothesis."""
    _get_or_raise(db, hypothesis_id)

    ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not ev:
        raise ValueError(f"Evidence {evidence_id} not found")

    existing = (
        db.query(HypothesisEvidence)
        .filter(
            HypothesisEvidence.hypothesis_id == hypothesis_id,
            HypothesisEvidence.evidence_id == evidence_id,
        )
        .first()
    )
    if existing:
        existing.direction = direction
        existing.weight = weight
        db.commit()
        db.refresh(existing)
        return existing

    link = HypothesisEvidence(
        hypothesis_id=hypothesis_id,
        evidence_id=evidence_id,
        direction=direction,
        weight=weight,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def unlink_evidence(db: Session, hypothesis_id: int, evidence_id: int) -> None:
    """Remove an evidence link from a hypothesis."""
    link = (
        db.query(HypothesisEvidence)
        .filter(
            HypothesisEvidence.hypothesis_id == hypothesis_id,
            HypothesisEvidence.evidence_id == evidence_id,
        )
        .first()
    )
    if not link:
        raise ValueError(
            f"No link between hypothesis {hypothesis_id} and evidence {evidence_id}"
        )
    db.delete(link)
    db.commit()


def compute_score(db: Session, hypothesis_id: int) -> float:
    """Compute weighted confidence score from linked evidence.

    score = sum(dir_factor * weight * confidence * type_weight) / sum(weight * type_weight)
    clamped to [0, 1]
    """
    hyp = _get_or_raise(db, hypothesis_id)

    links = (
        db.query(HypothesisEvidence)
        .options(joinedload(HypothesisEvidence.evidence))
        .filter(HypothesisEvidence.hypothesis_id == hypothesis_id)
        .all()
    )

    if not links:
        return 0.0

    numerator = 0.0
    denominator = 0.0

    for link in links:
        ev = link.evidence
        if ev is None:
            continue
        dir_factor = DIRECTION_FACTOR.get(link.direction.value, 0.0)
        type_weight = TYPE_WEIGHTS.get(ev.evidence_type.value, 1.0)
        confidence = ev.confidence or 0.5
        w = link.weight

        numerator += dir_factor * w * confidence * type_weight
        denominator += w * type_weight

    if denominator == 0:
        return 0.0

    score = max(0.0, min(1.0, numerator / denominator))

    hyp.confidence_score = score
    db.commit()

    return score


def list_hypotheses(
    db: Session,
    status: HypothesisStatus | None = None,
    gene_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Hypothesis]:
    """List hypotheses, optionally filtered by status and/or gene_id."""
    q = db.query(Hypothesis)
    if status is not None:
        q = q.filter(Hypothesis.status == status)
    if gene_id is not None:
        q = q.filter(Hypothesis.gene_id == gene_id)
    return q.order_by(Hypothesis.hypothesis_id).offset(offset).limit(limit).all()


def get_hypothesis(db: Session, hypothesis_id: int) -> Hypothesis | None:
    """Get a hypothesis by ID with evidence links loaded."""
    return (
        db.query(Hypothesis)
        .options(
            joinedload(Hypothesis.evidence_links).joinedload(HypothesisEvidence.evidence)
        )
        .filter(Hypothesis.hypothesis_id == hypothesis_id)
        .first()
    )


def get_hypothesis_for_gene(db: Session, gene_id: int) -> Hypothesis | None:
    """Get the latest hypothesis for a gene."""
    hyp = (
        db.query(Hypothesis)
        .options(
            joinedload(Hypothesis.evidence_links).joinedload(HypothesisEvidence.evidence)
        )
        .filter(Hypothesis.gene_id == gene_id)
        .order_by(Hypothesis.hypothesis_id.desc())
        .first()
    )
    if hyp:
        return hyp

    evidence_ids = [
        eid
        for (eid,) in db.query(Evidence.evidence_id)
        .filter(Evidence.gene_id == gene_id)
        .all()
    ]
    if not evidence_ids:
        return None

    return (
        db.query(Hypothesis)
        .join(HypothesisEvidence)
        .filter(HypothesisEvidence.evidence_id.in_(evidence_ids))
        .options(
            joinedload(Hypothesis.evidence_links).joinedload(HypothesisEvidence.evidence)
        )
        .order_by(Hypothesis.hypothesis_id.desc())
        .first()
    )


def _get_or_raise(db: Session, hypothesis_id: int) -> Hypothesis:
    """Get hypothesis or raise HypothesisNotFoundError."""
    hyp = db.query(Hypothesis).filter(Hypothesis.hypothesis_id == hypothesis_id).first()
    if not hyp:
        raise HypothesisNotFoundError(f"Hypothesis {hypothesis_id} not found")
    return hyp
