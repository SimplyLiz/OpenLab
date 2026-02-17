"""Dedicated feed query builder with filtering and sorting."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from openlab.researchbook.models import ResearchThread, ThreadStatus


def build_feed_query(
    db: Session,
    gene_symbol: str | None = None,
    cancer_type: str | None = None,
    status: str | None = None,
    sort_by: str = "recent",
    published_only: bool = True,
):
    """Build a filtered, sorted query for the feed."""
    q = db.query(ResearchThread)

    if published_only:
        q = q.filter(ResearchThread.status.in_([
            ThreadStatus.PUBLISHED.value,
            ThreadStatus.CHALLENGED.value,
        ]))

    if gene_symbol:
        q = q.filter(ResearchThread.gene_symbol == gene_symbol)
    if cancer_type:
        q = q.filter(ResearchThread.cancer_type == cancer_type)
    if status:
        q = q.filter(ResearchThread.status == status)

    if sort_by == "convergence":
        q = q.order_by(desc(ResearchThread.convergence_score))
    elif sort_by == "challenges":
        q = q.order_by(desc(ResearchThread.challenge_count))
    elif sort_by == "forks":
        q = q.order_by(desc(ResearchThread.fork_count))
    else:
        q = q.order_by(desc(ResearchThread.created_at))

    return q
