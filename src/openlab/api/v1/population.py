"""Population simulation API endpoint."""

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openlab.models import CellSpec

router = APIRouter(prefix="/simulation", tags=["simulation"])

logger = logging.getLogger(__name__)


class PopulationRequest(BaseModel):
    cellspec: dict
    grid_size: int = 8
    duration: float = 7200.0
    mutation_rate: float = 1e-4
    seed: int = 42


class PopulationResult(BaseModel):
    snapshots: list[dict] = []
    summary: dict = {}


@router.post("/population", response_model=PopulationResult)
def run_population_simulation(body: PopulationRequest):
    """Run a multi-cell population simulation on a 2D grid.

    Requires a previously assembled CellSpec with stochastic=True.
    """
    try:
        spec = CellSpec.model_validate(body.cellspec)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid CellSpec: {e}. Run the full pipeline first.",
        )

    # Override spec params with request values
    spec.simulation_parameters.stochastic = True
    spec.simulation_parameters.grid_size = body.grid_size
    spec.simulation_parameters.mutation_rate = body.mutation_rate
    spec.simulation_parameters.seed = body.seed

    from openlab.simulation.population import PopulationEngine

    start_time = time.perf_counter()
    engine = PopulationEngine(spec, seed=body.seed)
    snapshots = engine.run(body.duration)
    wall_time = time.perf_counter() - start_time

    summary = {}
    if snapshots:
        final = snapshots[-1]
        summary = {
            "total_cells": final.get("total_cells", 0),
            "generations_max": final.get("generations_max", 0),
            "total_mutations": final.get("total_mutations", 0),
            "mean_fitness": final.get("mean_fitness", 0.0),
            "wall_time_seconds": round(wall_time, 2),
            "num_snapshots": len(snapshots),
        }

    return PopulationResult(snapshots=snapshots, summary=summary)
