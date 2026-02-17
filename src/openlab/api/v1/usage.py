"""Usage tracking endpoints — session totals, historical aggregates, recent calls."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from openlab.api.deps import get_db
from openlab.api.v1.schemas import UsageLogEntry, UsageSessionResponse, UsageTotalResponse
from openlab.services import usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/session", response_model=UsageSessionResponse)
def session_totals():
    """In-memory usage totals since process start (no DB hit)."""
    return usage_service.get_session_totals()


@router.get("/total", response_model=UsageTotalResponse)
def total_usage(db: Session = Depends(get_db)):
    """All-time aggregated usage from the database."""
    return usage_service.get_total_usage(db)


@router.get("/recent", response_model=list[UsageLogEntry])
def recent_calls(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Most recent API usage log entries."""
    return usage_service.get_recent_calls(db, limit=limit)
