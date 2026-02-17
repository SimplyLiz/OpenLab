"""FastAPI application factory (PRD §7)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CellForge API",
        description="Genome-agnostic whole-cell simulation engine",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from openlab.cellforge.api.routes.annotation import router as annotation_router
    from openlab.cellforge.api.routes.health import router as health_router
    from openlab.cellforge.api.routes.simulation import router as simulation_router

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(simulation_router, prefix="/api/v1")
    app.include_router(annotation_router, prefix="/api/v1")

    return app
