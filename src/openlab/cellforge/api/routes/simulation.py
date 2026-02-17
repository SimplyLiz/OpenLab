"""Simulation API routes (PRD §7.1)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from openlab.cellforge.api.schemas import (
    PerturbationRequest,
    SimulationCreateRequest,
    SimulationCreateResponse,
    SimulationStateResponse,
    SimulationStatusResponse,
)
from openlab.cellforge.core.config import SimulationConfig
from openlab.cellforge.core.simulation import Simulation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulations", tags=["simulations"])

# In-memory simulation store
_simulations: dict[str, dict[str, Any]] = {}


def _get_sim(simulation_id: str) -> dict[str, Any]:
    if simulation_id not in _simulations:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    return _simulations[simulation_id]


@router.post("/", response_model=SimulationCreateResponse)
async def create_simulation(request: SimulationCreateRequest) -> SimulationCreateResponse:
    """Create a new simulation."""
    sim_id = str(uuid.uuid4())[:8]

    config = SimulationConfig(
        organism_name=request.organism_name,
        genome_fasta=request.genome_fasta,
        **{k: v for k, v in request.config.items() if hasattr(SimulationConfig, k)},
    )

    sim = Simulation(config=config)
    sim.initialize()

    _simulations[sim_id] = {
        "simulation": sim,
        "status": "created",
        "task": None,
    }

    logger.info("Created simulation %s for %s", sim_id, request.organism_name)
    return SimulationCreateResponse(simulation_id=sim_id, status="created")


@router.get("/{simulation_id}", response_model=SimulationStatusResponse)
async def get_simulation_status(simulation_id: str) -> SimulationStatusResponse:
    """Get simulation status."""
    entry = _get_sim(simulation_id)
    sim: Simulation = entry["simulation"]
    state = sim.get_state()

    return SimulationStatusResponse(
        simulation_id=simulation_id,
        status=entry["status"],
        time=state.get("time", 0.0),
        total_time=sim.config.total_time,
        progress=state.get("time", 0.0) / sim.config.total_time if sim.config.total_time > 0 else 0.0,
    )


@router.post("/{simulation_id}/start")
async def start_simulation(simulation_id: str) -> dict[str, str]:
    """Start a simulation in the background."""
    entry = _get_sim(simulation_id)

    if entry["status"] == "running":
        raise HTTPException(status_code=409, detail="Simulation already running")

    sim: Simulation = entry["simulation"]
    entry["status"] = "running"

    async def _run_sim() -> None:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, sim.run)
            entry["status"] = "completed"
        except Exception:
            logger.exception("Simulation %s failed", simulation_id)
            entry["status"] = "error"

    task = asyncio.create_task(_run_sim())
    entry["task"] = task

    return {"status": "started", "simulation_id": simulation_id}


@router.post("/{simulation_id}/stop")
async def stop_simulation(simulation_id: str) -> dict[str, str]:
    """Stop a running simulation."""
    entry = _get_sim(simulation_id)
    sim: Simulation = entry["simulation"]
    sim.stop()
    entry["status"] = "stopped"
    return {"status": "stopped", "simulation_id": simulation_id}


@router.get("/{simulation_id}/state", response_model=SimulationStateResponse)
async def get_simulation_state(simulation_id: str) -> SimulationStateResponse:
    """Get current simulation state."""
    entry = _get_sim(simulation_id)
    sim: Simulation = entry["simulation"]
    state = sim.get_state()

    # Return a JSON-safe subset of state
    safe_state: dict[str, object] = {
        "metabolite_concentrations": state.get("metabolite_concentrations", {}),
        "mrna_counts": {k: v for k, v in state.get("mrna_counts", {}).items()},
        "protein_counts": {k: v for k, v in state.get("protein_counts", {}).items()},
        "flux_distribution": state.get("flux_distribution", {}),
        "growth_rate": state.get("growth_rate", 0.0),
        "cell_mass": state.get("cell_mass", 0.0),
        "replication_progress": state.get("replication_progress", 0.0),
    }

    return SimulationStateResponse(
        simulation_id=simulation_id,
        time=state.get("time", 0.0),
        state=safe_state,
    )


@router.post("/{simulation_id}/perturbation")
async def inject_perturbation(simulation_id: str, request: PerturbationRequest) -> dict[str, str]:
    """Inject a perturbation into a running simulation."""
    entry = _get_sim(simulation_id)
    sim: Simulation = entry["simulation"]

    try:
        sim.inject_perturbation(
            perturbation_type=request.perturbation_type,
            target=request.target,
            value=request.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"status": "applied", "perturbation_type": request.perturbation_type, "target": request.target}


@router.get("/{simulation_id}/history")
async def get_simulation_history(simulation_id: str) -> dict[str, Any]:
    """Get simulation history."""
    entry = _get_sim(simulation_id)
    sim: Simulation = entry["simulation"]
    return {"simulation_id": simulation_id, "history": sim.get_history()}
