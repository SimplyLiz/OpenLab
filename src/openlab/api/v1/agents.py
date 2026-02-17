"""Agent API routes — dossier generation, run management, provenance."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


# --- Schemas ---


class DossierRequest(BaseModel):
    gene_symbol: str
    cancer_type: str | None = None


class DossierResponse(BaseModel):
    run_id: str
    status: str = "started"


class AgentRunOut(BaseModel):
    run_id: str
    gene_symbol: str
    cancer_type: str | None = None
    status: str
    total_tool_calls: int = 0
    error: str | None = None


class ProvenanceEntryOut(BaseModel):
    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
    success: bool = True
    sources: list[str] = Field(default_factory=list)
    parent_call_id: str | None = None
    error: str | None = None


class ClaimOut(BaseModel):
    claim_text: str
    confidence: float = 0.0
    citations: list[str] = Field(default_factory=list)
    citation_status: str = "unchecked"
    is_speculative: bool = False


# --- In-memory run storage (production would use DB) ---

_active_runs: dict[str, dict] = {}
_dossier_events: dict[str, list[dict]] = {}


# --- Routes ---


@router.post("/dossier", response_model=DossierResponse)
async def start_dossier(request: DossierRequest):
    """Start a dossier generation run. Returns run_id for streaming."""
    from openlab.agents.runner import run_dossier_agent

    run_id_holder: dict[str, str] = {}

    async def _background():
        events = []
        async for event in run_dossier_agent(request.gene_symbol, request.cancer_type):
            events.append(event.model_dump(mode="json"))
            if not run_id_holder.get("id"):
                run_id_holder["id"] = event.run_id
        run_id = run_id_holder.get("id", "")
        _dossier_events[run_id] = events
        _active_runs[run_id] = {
            "gene_symbol": request.gene_symbol,
            "cancer_type": request.cancer_type,
            "status": "completed",
            "events": events,
        }

    # Start background task
    task = asyncio.create_task(_background())

    # Wait briefly for run_id to be set
    for _ in range(50):
        if run_id_holder.get("id"):
            break
        await asyncio.sleep(0.05)

    run_id = run_id_holder.get("id", "pending")
    _active_runs[run_id] = {
        "gene_symbol": request.gene_symbol,
        "cancer_type": request.cancer_type,
        "status": "running",
        "task": task,
    }

    return DossierResponse(run_id=run_id)


@router.get("/dossier/{run_id}")
async def get_dossier(run_id: str):
    """Get completed dossier results."""
    run = _active_runs.get(run_id)
    if not run:
        return {"error": "Run not found", "run_id": run_id}
    events = _dossier_events.get(run_id, [])
    return {
        "run_id": run_id,
        "gene_symbol": run.get("gene_symbol"),
        "cancer_type": run.get("cancer_type"),
        "status": run.get("status"),
        "events": events,
    }


@router.websocket("/dossier/{run_id}/stream")
async def stream_dossier(websocket: WebSocket, run_id: str):
    """Stream agent events for a dossier run via WebSocket."""
    await websocket.accept()
    try:
        from openlab.agents.runner import run_dossier_agent

        run = _active_runs.get(run_id)
        if not run:
            await websocket.send_json({"error": "Run not found"})
            return

        gene_symbol = run.get("gene_symbol", "")
        cancer_type = run.get("cancer_type")

        async for event in run_dossier_agent(gene_symbol, cancer_type):
            await websocket.send_json(event.model_dump(mode="json"))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


@router.post("/run", response_model=DossierResponse)
async def agent_run(request: DossierRequest):
    """Free-form agent run (alias for dossier)."""
    return await start_dossier(request)


@router.get("/runs", response_model=list[AgentRunOut])
async def list_runs():
    """List all agent runs."""
    runs = []
    for run_id, run in _active_runs.items():
        runs.append(
            AgentRunOut(
                run_id=run_id,
                gene_symbol=run.get("gene_symbol", ""),
                cancer_type=run.get("cancer_type"),
                status=run.get("status", "unknown"),
            )
        )
    return runs


@router.get("/runs/{run_id}/provenance", response_model=list[ProvenanceEntryOut])
async def get_provenance(run_id: str):
    """Get full provenance chain for a run."""
    events = _dossier_events.get(run_id, [])
    # Extract provenance from DOSSIER_COMPLETED event
    for ev in events:
        if ev.get("event_type") == "dossier_completed":
            return ev.get("data", {}).get("provenance", [])
    return []
