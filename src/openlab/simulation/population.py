"""Population simulation engine.

Runs multiple cells on a 2D spatial grid with diffusing nutrients,
resource competition, stochastic division, mutations, and epigenetics.
"""
from __future__ import annotations

import copy
import logging
import math

import numpy as np

from openlab.models import CellSpec, CellSnapshotData
from openlab.simulation.diffusion import diffuse_2d, replenish_edges
from openlab.simulation.epigenetics import EpigeneticsModule
from openlab.simulation.gene_expression import GeneExpressionModule
from openlab.simulation.growth import GrowthModule
from openlab.simulation.metabolism import MetabolismModule
from openlab.simulation.mutation import MutationModule
from openlab.simulation.state import CellState

logger = logging.getLogger(__name__)

# Base glucose concentration for edge replenishment (mM)
BASE_GLUCOSE = 5.0
REPLENISH_RATE = 0.05


class PopulationEngine:
    """Multi-cell population simulation on a 2D nutrient grid."""

    def __init__(
        self,
        spec: CellSpec,
        *,
        seed: int = 42,
        on_progress: callable | None = None,
    ):
        self.spec = spec
        self.grid_size = spec.simulation_parameters.grid_size
        self.rng = np.random.default_rng(seed)
        self._on_progress = on_progress

        # Grid state
        self.cells: dict[tuple[int, int], CellState] = {}
        self.nutrient_field = np.full(
            (self.grid_size, self.grid_size), BASE_GLUCOSE, dtype=np.float64
        )

        # Seed one cell at center
        center = self.grid_size // 2
        cell = CellState.from_spec(spec, seed=seed)
        cell.cell_id = 0
        self.cells[(center, center)] = cell
        self._next_cell_id = 1

        # Shared modules
        self._metabolism = MetabolismModule(spec.reactions)
        self._expression = GeneExpressionModule(spec.genes, stochastic=True)
        self._growth = GrowthModule(stochastic=True)
        self._mutation = MutationModule(spec.simulation_parameters.mutation_rate)
        self._epigenetics = EpigeneticsModule()

        self._metabolism_dt = spec.simulation_parameters.metabolism_dt
        self._expression_dt = spec.simulation_parameters.expression_dt
        self._diffusion_rate = spec.simulation_parameters.nutrient_diffusion_rate

    def run(self, duration: float) -> list[dict]:
        """Run population simulation, return list of snapshot dicts."""
        snapshots: list[dict] = []
        record_interval = 60.0
        next_record_time = 0.0
        num_sub_steps = round(self._expression_dt / self._metabolism_dt)
        total_macro_steps = math.ceil(duration / self._expression_dt)

        snapshots.append(self._snapshot(0.0))

        for step_idx in range(total_macro_steps):
            current_time = (step_idx + 1) * self._expression_dt
            self._step_all(num_sub_steps)

            if current_time >= next_record_time:
                snapshots.append(self._snapshot(current_time))
                next_record_time += record_interval

            if (step_idx + 1) % 100 == 0:
                pct = (step_idx + 1) / total_macro_steps * 100
                logger.info(
                    f"[PopEngine] {pct:.1f}% t={current_time:.0f}s "
                    f"cells={len(self.cells)}"
                )
                if self._on_progress:
                    self._on_progress(pct, current_time, self._snapshot(current_time))

        snapshots.append(self._snapshot(duration))
        return snapshots

    def _step_all(self, num_sub_steps: int) -> None:
        """One macro-step: run all cells, diffuse nutrients, handle divisions."""
        divisions: list[tuple[int, int]] = []

        for pos, cell in list(self.cells.items()):
            # Feed cell from local nutrient
            local_glucose = float(self.nutrient_field[pos])
            cell.set_metabolite("glucose", local_glucose)

            # Run sub-steps: metabolism + expression
            for _ in range(num_sub_steps):
                self._metabolism.step(cell, self._metabolism_dt)
                self._expression.step(cell, self._metabolism_dt)
                cell.time += self._metabolism_dt

            # Growth check
            divided = self._growth.step(cell, self._expression_dt)
            if divided:
                self._mutation.apply_division_mutations(cell, self.spec.genes)
                divisions.append(pos)

            # Epigenetics
            self._epigenetics.step(cell, self.spec.genes)

            # Write back consumed nutrients
            consumed_glucose = cell.get_metabolite("glucose")
            self.nutrient_field[pos] = max(0.0, consumed_glucose)

        # Place daughters in neighboring empty cells
        for parent_pos in divisions:
            self._try_place_daughter(parent_pos)

        # Diffuse + replenish nutrients
        self.nutrient_field = diffuse_2d(
            self.nutrient_field, self._diffusion_rate, self._expression_dt
        )
        self.nutrient_field = replenish_edges(
            self.nutrient_field, BASE_GLUCOSE, REPLENISH_RATE
        )

    def _try_place_daughter(self, parent_pos: tuple[int, int]) -> bool:
        """Clone parent state into a random empty neighbor. Returns False if blocked."""
        r, c = parent_pos
        neighbors = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr = (r + dr) % self.grid_size
                nc = (c + dc) % self.grid_size
                if (nr, nc) not in self.cells:
                    neighbors.append((nr, nc))

        if not neighbors:
            return False

        target = neighbors[self.rng.integers(len(neighbors))]
        parent = self.cells[parent_pos]

        # Create daughter as deep copy of parent state
        daughter = CellState(
            time=parent.time,
            metabolite_concentrations=parent.metabolite_concentrations.copy(),
            protein_counts=parent.protein_counts.copy(),
            mrna_counts=parent.mrna_counts.copy(),
            volume=parent.volume,
            metabolite_index=parent.metabolite_index,
            gene_index=parent.gene_index,
            dry_mass=parent.dry_mass,
            growth_rate=parent.growth_rate,
            mass_accumulated=0.0,
            division_count=parent.division_count,
            knocked_out_genes=set(parent.knocked_out_genes),
            rng=np.random.default_rng(self.rng.integers(2**31)),
            gene_expression_modifiers=parent.gene_expression_modifiers.copy(),
            mutations=dict(parent.mutations),
            methylation=parent.methylation.copy(),
            cell_id=self._next_cell_id,
            parent_id=parent.cell_id,
            generation=parent.generation,
        )
        self._next_cell_id += 1
        self.cells[target] = daughter
        return True

    def _snapshot(self, time: float) -> dict:
        """Capture population snapshot as dict."""
        cells_data = []
        total_mutations = 0
        max_gen = 0
        fitness_sum = 0.0

        for (r, c), cell in self.cells.items():
            mutation_count = len(cell.mutations)
            total_mutations += mutation_count
            max_gen = max(max_gen, cell.generation)
            fitness_sum += cell.growth_rate

            cells_data.append(
                CellSnapshotData(
                    cell_id=cell.cell_id,
                    row=r,
                    col=c,
                    generation=cell.generation,
                    volume=cell.volume,
                    growth_rate=cell.growth_rate,
                    mutation_count=mutation_count,
                    fitness=cell.growth_rate,
                ).model_dump()
            )

        n_cells = len(self.cells)
        return {
            "time": time,
            "total_cells": n_cells,
            "grid_size": self.grid_size,
            "cells": cells_data,
            "nutrient_field": self.nutrient_field.tolist(),
            "mean_fitness": fitness_sum / n_cells if n_cells > 0 else 0.0,
            "total_mutations": total_mutations,
            "generations_max": max_gen,
        }
