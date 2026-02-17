"""Stage: Simulation — run whole-cell simulation from CellSpec."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from openlab.models import CellSpec, PipelineEvent, SimulationResult, SimulationSnapshot, StageStatus
from openlab.simulation import SimulationEngine

logger = logging.getLogger(__name__)

STAGE = "simulation"


async def run(cellspec: CellSpec) -> AsyncGenerator[PipelineEvent, None]:
    """Run whole-cell simulation, streaming snapshots as progress events."""
    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.0,
        data={"message": "Starting simulation..."},
    )

    wall_start = time.monotonic()
    progress_events: list[tuple[float, float, dict]] = []

    def on_progress(pct: float, sim_time: float, snapshot: dict) -> None:
        progress_events.append((pct, sim_time, snapshot))

    engine = SimulationEngine(cellspec, on_progress=on_progress)

    # Run simulation in thread pool to avoid blocking event loop
    result_dict = await asyncio.to_thread(engine.run_to_dict)

    # Emit progress events
    for pct, sim_time, snapshot in progress_events:
        wall_elapsed = time.monotonic() - wall_start
        yield PipelineEvent(
            stage=STAGE, status=StageStatus.RUNNING,
            progress=pct / 100.0,
            data={
                "snapshot": snapshot,
                "progress": pct / 100.0,
                "simulated_time": sim_time,
                "wall_time": round(wall_elapsed, 2),
            },
        )

    wall_total = time.monotonic() - wall_start
    summary = result_dict.get("summary", {})
    time_series = result_dict.get("timeSeries", [])

    summary["wall_time_seconds"] = round(wall_total, 2)

    yield PipelineEvent(
        stage=STAGE,
        status=StageStatus.COMPLETED,
        progress=1.0,
        data={
            "summary": summary,
            "time_series": time_series,
            "total_divisions": summary.get("divisions", 0),
            "doubling_time": summary.get("doublingTimeHours"),
        },
    )
