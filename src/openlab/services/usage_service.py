"""Usage service — records and queries LLM API token consumption."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from openlab.db.engine import get_session_factory
from openlab.db.models.api_usage import APIUsageLog

logger = logging.getLogger(__name__)

# --- Cost per 1K tokens (USD) ---

COST_PER_1K: dict[str, dict[str, float]] = {
    "anthropic": {"input": 0.003, "output": 0.015},
    "openai": {"input": 0.0025, "output": 0.010},
    "ollama": {"input": 0.0, "output": 0.0},
}

# --- In-memory session accumulator (resets on process restart) ---

_session: dict[str, Any] = {
    "total_calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "estimated_cost_usd": 0.0,
    "by_gene": {},
}


def _estimate_cost(provider: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = COST_PER_1K.get(provider, COST_PER_1K["openai"])
    return round(
        (prompt_tokens / 1000) * rates["input"]
        + (completion_tokens / 1000) * rates["output"],
        6,
    )


def record_usage(
    *,
    provider: str,
    model: str,
    purpose: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: int,
    success: bool = True,
    error_message: str | None = None,
    gene_locus_tag: str | None = None,
) -> None:
    """Update in-memory accumulator and persist an APIUsageLog row."""
    total_tokens = prompt_tokens + completion_tokens
    cost = _estimate_cost(provider, prompt_tokens, completion_tokens)

    # Update in-memory session totals
    _session["total_calls"] += 1
    _session["prompt_tokens"] += prompt_tokens
    _session["completion_tokens"] += completion_tokens
    _session["total_tokens"] += total_tokens
    _session["estimated_cost_usd"] = round(_session["estimated_cost_usd"] + cost, 6)

    if gene_locus_tag:
        bg = _session["by_gene"]
        if gene_locus_tag not in bg:
            bg[gene_locus_tag] = {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            }
        g = bg[gene_locus_tag]
        g["calls"] += 1
        g["prompt_tokens"] += prompt_tokens
        g["completion_tokens"] += completion_tokens
        g["total_tokens"] += total_tokens
        g["estimated_cost_usd"] = round(g["estimated_cost_usd"] + cost, 6)

    # Persist to DB (own session, never breaks caller)
    try:
        factory = get_session_factory()
        db = factory()
        try:
            row = APIUsageLog(
                provider=provider,
                model=model,
                purpose=purpose,
                gene_locus_tag=gene_locus_tag,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
            )
            db.add(row)
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.debug("Failed to persist API usage log row", exc_info=True)


def get_session_totals() -> dict[str, Any]:
    """Return in-memory session accumulator (no DB hit)."""
    return _session.copy()


def get_total_usage(db: Session) -> dict[str, Any]:
    """Aggregate all-time usage from api_usage_log table."""
    row = db.query(
        func.count(APIUsageLog.id).label("total_calls"),
        func.coalesce(func.sum(APIUsageLog.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(APIUsageLog.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(APIUsageLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(APIUsageLog.estimated_cost_usd), 0).label("estimated_cost_usd"),
    ).one()
    return {
        "total_calls": row.total_calls,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "total_tokens": row.total_tokens,
        "estimated_cost_usd": round(float(row.estimated_cost_usd), 6),
    }


def get_recent_calls(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent API usage log entries."""
    rows = (
        db.query(APIUsageLog)
        .order_by(APIUsageLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "provider": r.provider,
            "model": r.model,
            "purpose": r.purpose,
            "gene_locus_tag": r.gene_locus_tag,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "estimated_cost_usd": r.estimated_cost_usd,
            "duration_ms": r.duration_ms,
            "success": r.success,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
