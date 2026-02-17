"""OpenLab unified FastAPI application — WebSocket streaming + REST CRUD."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from openlab.config import config
from openlab.models import GeneInput, PipelineEvent, StageStatus
from openlab.pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared resources: httpx client + DB auto-create in dev mode."""
    app.state.http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    # Auto-create SQLite tables in dev mode (no alembic needed for quick start)
    if config.database.url.startswith("sqlite"):
        try:
            from openlab.db.models.base import Base
            from openlab.db import get_engine
            Base.metadata.create_all(get_engine())
        except Exception:
            pass

    yield
    await app.state.http.aclose()


def create_app() -> FastAPI:
    """Application factory — returns configured FastAPI instance."""
    app = FastAPI(
        title="OpenLab",
        version="0.1.0",
        description="Unified bioinformatics platform — gene analysis, evidence management, and whole-cell simulation",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    _register_exception_handlers(app)

    # REST API v1 routes (DNASyn CRUD)
    from openlab.api.v1.router import router as v1_router
    app.include_router(v1_router)

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    # Non-streaming fallback
    @app.post("/api/analyze")
    async def analyze_gene(gene_input: GeneInput):
        results: dict[str, dict] = {}
        async for event in run_pipeline(gene_input, app.state.http):
            if event.status == StageStatus.COMPLETED and event.data:
                results[event.stage] = event.data
            elif event.status == StageStatus.FAILED:
                results[event.stage] = {"error": event.error}
        return {"gene": gene_input.query, "results": results}

    # WebSocket streaming
    @app.websocket("/ws/analyze")
    async def ws_analyze(websocket: WebSocket):
        await websocket.accept()
        try:
            from openlab.db import get_session_factory
            from openlab.pipeline.persistence import persist_event

            SessionLocal = get_session_factory()
            data = await websocket.receive_json()

            if "protein_sequence" in data:
                # Deep single-gene analysis (triggered by clicking a gene)
                from openlab.pipeline.stages.functional_prediction import run_single_gene

                async for event in run_single_gene(
                    locus_tag=data["locus_tag"],
                    protein_sequence=data["protein_sequence"],
                    gene_name=data.get("gene_name", ""),
                    product=data.get("product", ""),
                    http=websocket.app.state.http,
                ):
                    await websocket.send_json(event.model_dump())

                    if event.status == StageStatus.COMPLETED and event.data:
                        try:
                            with SessionLocal() as db:
                                persist_event(db, event.stage, event.data)
                        except Exception as e:
                            logger.warning("Persistence failed for %s: %s", event.stage, e)
            else:
                # Normal pipeline (genome or single gene via search box)
                gene_input = GeneInput(**data)

                async for event in run_pipeline(gene_input, websocket.app.state.http):
                    await websocket.send_json(event.model_dump())

                    if event.status == StageStatus.COMPLETED and event.data:
                        try:
                            with SessionLocal() as db:
                                persist_event(db, event.stage, event.data)
                        except Exception as e:
                            logger.warning("Persistence failed for %s: %s", event.stage, e)

                await websocket.send_json(
                    PipelineEvent(
                        stage="persistence", status=StageStatus.COMPLETED,
                        data={"stored": True}, progress=1.0,
                    ).model_dump()
                )
                await websocket.send_json(
                    PipelineEvent(
                        stage="pipeline", status=StageStatus.COMPLETED, progress=1.0
                    ).model_dump()
                )
        except WebSocketDisconnect:
            pass
        except Exception as e:
            try:
                await websocket.send_json(
                    PipelineEvent(
                        stage="pipeline", status=StageStatus.FAILED, error=str(e)
                    ).model_dump()
                )
            except Exception:
                pass

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers for domain errors."""
    import time
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from openlab.exceptions import GeneNotFoundError, ParseError, ImportError_, BioLabError

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response

    @app.exception_handler(GeneNotFoundError)
    async def gene_not_found_handler(request: Request, exc: GeneNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ParseError)
    async def parse_error_handler(request: Request, exc: ParseError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ImportError_)
    async def import_error_handler(request: Request, exc: ImportError_):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(BioLabError)
    async def biolab_error_handler(request: Request, exc: BioLabError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})
