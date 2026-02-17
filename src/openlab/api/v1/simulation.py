"""Simulation API endpoints — knockout simulation."""

import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openlab.models import CellSpec

router = APIRouter(prefix="/simulation", tags=["simulation"])

logger = logging.getLogger(__name__)


class KnockoutRequest(BaseModel):
    genome_id: int
    knockouts: list[str] = []
    cellspec: dict  # CellSpec as dict (sent from frontend store)


class KnockoutResult(BaseModel):
    metadata: dict = {}
    time_series: list[dict] = []
    summary: dict = {}


@router.post("/knockout", response_model=KnockoutResult)
def run_knockout_simulation(body: KnockoutRequest):
    """Run ODE simulation with knocked-out genes.

    Expects the CellSpec from the frontend (previously assembled by the pipeline).
    Runs SimulationEngine with the knockout set applied.
    """
    try:
        spec = CellSpec.model_validate(body.cellspec)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid CellSpec: {e}. Run the full pipeline first.",
        )

    from openlab.simulation.engine import SimulationEngine

    knockout_set = set(body.knockouts)

    start_time = time.perf_counter()
    engine = SimulationEngine(spec, knockouts=knockout_set)
    result = engine.run_to_dict()
    wall_time = time.perf_counter() - start_time

    result["summary"]["wall_time_seconds"] = round(wall_time, 2)
    result["summary"]["knockouts"] = sorted(knockout_set)

    time_series = result.get("timeSeries", [])

    return KnockoutResult(
        metadata=result.get("metadata", {}),
        time_series=time_series,
        summary=result.get("summary", {}),
    )
