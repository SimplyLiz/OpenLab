"""Main simulation engine for whole-cell modeling.

Multi-timescale ODE simulation with interleaved metabolism and gene expression,
plus growth/division tracking.

Scheduler architecture:
  Per macro-step (60s simulated time):
    120x sub-steps, each containing:
      1x metabolism (dt = 0.5s)
      1x gene expression (dt = 0.5s)
    1x growth check (at end of macro-step)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from openlab.models import CellSpec
from openlab.simulation.gene_expression import GeneExpressionModule
from openlab.simulation.growth import GrowthModule
from openlab.simulation.metabolism import MetabolismModule
from openlab.simulation.state import CellState

logger = logging.getLogger(__name__)


@dataclass
class SimulationRecord:
    """Time-series output record."""
    time: float
    data: dict

    def to_dict(self) -> dict:
        return {"time": self.time, **self.data}


class SimulationEngine:
    """Main simulation engine for whole-cell modeling."""

    def __init__(
        self,
        spec: CellSpec,
        *,
        record_interval: float = 60.0,
        knockouts: set[str] | None = None,
        on_progress: callable | None = None,
    ):
        self.spec = spec
        self.record_interval = record_interval
        self.knockouts = knockouts or set()
        self._on_progress = on_progress

        stochastic = spec.simulation_parameters.stochastic

        self._metabolism = MetabolismModule(spec.reactions)
        self._expression = GeneExpressionModule(spec.genes, stochastic=stochastic)
        self._growth = GrowthModule(stochastic=stochastic)

        # Mutation and epigenetics modules (only when stochastic)
        self._mutation = None
        self._epigenetics = None
        if stochastic:
            from openlab.simulation.mutation import MutationModule
            from openlab.simulation.epigenetics import EpigeneticsModule
            self._mutation = MutationModule(spec.simulation_parameters.mutation_rate)
            self._epigenetics = EpigeneticsModule()

        self._metabolism_dt = spec.simulation_parameters.metabolism_dt
        self._expression_dt = spec.simulation_parameters.expression_dt

    def run(self, duration: float | None = None) -> list[SimulationRecord]:
        """Run the simulation for the specified duration."""
        total_duration = duration or self.spec.simulation_parameters.total_duration
        seed = self.spec.simulation_parameters.seed
        state = CellState.from_spec(self.spec, knockouts=self.knockouts, seed=seed)
        records: list[SimulationRecord] = []

        self._log(
            f"Starting simulation: {total_duration}s, "
            f"metabolism dt={self._metabolism_dt}s, "
            f"expression dt={self._expression_dt}s"
            f"{', stochastic' if self.spec.simulation_parameters.stochastic else ''}"
        )

        records.append(SimulationRecord(0.0, state.snapshot()))

        next_record_time = self.record_interval
        num_sub_steps = round(self._expression_dt / self._metabolism_dt)
        total_macro_steps = math.ceil(total_duration / self._expression_dt)

        for step in range(total_macro_steps):
            if state.has_numerical_issue():
                self._log(f"WARNING: Numerical instability at t={state.time}s")
                break

            for _ in range(num_sub_steps):
                self._metabolism.step(state, self._metabolism_dt)
                self._expression.step(state, self._metabolism_dt)
                state.time += self._metabolism_dt

            divided = self._growth.step(state, self._expression_dt)

            # Post-division: apply mutations and epigenetics
            if divided and self._mutation is not None:
                self._mutation.apply_division_mutations(state, self.spec.genes)

            if self._epigenetics is not None:
                self._epigenetics.step(state, self.spec.genes)

            if state.time >= next_record_time:
                records.append(SimulationRecord(state.time, state.snapshot()))
                next_record_time += self.record_interval

            if (step + 1) % 100 == 0:
                pct = (step + 1) / total_macro_steps * 100
                self._log(
                    f"Progress: {pct:.1f}% (t={state.time:.0f}s, "
                    f"growthRate={state.growth_rate:.2e}, "
                    f"divisions={state.division_count})"
                )
                if self._on_progress:
                    self._on_progress(pct, state.time, state.snapshot())

        records.append(SimulationRecord(state.time, state.snapshot()))

        self._log(
            f"Simulation complete: {state.time}s, "
            f"{state.division_count} divisions, "
            f"{len(records)} records"
        )

        return records

    def run_to_dict(self, duration: float | None = None) -> dict:
        """Run simulation and return full output as a dict."""
        records = self.run(duration=duration)

        return {
            "metadata": {
                "organism": self.spec.organism,
                "specVersion": self.spec.version,
                "duration": duration or self.spec.simulation_parameters.total_duration,
                "metabolismDt": self._metabolism_dt,
                "expressionDt": self._expression_dt,
                "numGenes": len(self.spec.genes),
                "numReactions": len(self.spec.reactions),
                "numMetabolites": len(self.spec.metabolites),
                "stochastic": self.spec.simulation_parameters.stochastic,
                "seed": self.spec.simulation_parameters.seed,
                **({"knockouts": sorted(self.knockouts)} if self.knockouts else {}),
            },
            "timeSeries": [r.to_dict() for r in records],
            "summary": self._compute_summary(records),
        }

    def _compute_summary(self, records: list[SimulationRecord]) -> dict:
        if not records:
            return {}

        last = records[-1]
        divisions = last.data.get("divisionCount", 0)
        total_time = last.time

        doubling_time = None
        growth_rate = last.data.get("growthRate", 0.0)
        if growth_rate > 0:
            doubling_time = 0.693 / growth_rate
        elif divisions > 0:
            doubling_time = total_time / divisions

        return {
            "totalSimulatedTime": total_time,
            "divisions": divisions,
            "doublingTimeSeconds": doubling_time,
            "doublingTimeHours": doubling_time / 3600 if doubling_time else None,
            "finalGrowthRate": last.data.get("growthRate"),
            "finalVolume": last.data.get("volume"),
            "finalDryMass": last.data.get("dryMass"),
        }

    def _log(self, message: str) -> None:
        logger.info(f"[SimEngine] {message}")
