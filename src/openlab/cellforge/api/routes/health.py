"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

from openlab.cellforge.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    engine_available = False
    try:
        from openlab.cellforge._engine import __version__  # noqa: F401

        engine_available = True
    except ImportError:
        pass

    return HealthResponse(
        status="ok",
        version="0.1.0",
        engine_available=engine_available,
    )
