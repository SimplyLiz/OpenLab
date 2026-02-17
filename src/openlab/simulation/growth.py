"""Growth and division simulation module.

Tracks mass accumulation from protein synthesis and triggers
cell division when mass doubles.
"""
from __future__ import annotations

import math

import numpy as np

from openlab.simulation.state import CellState

# M. genitalium physical constants (Maier 2011)
INITIAL_DRY_MASS = 10.5    # femtograms
INITIAL_VOLUME = 0.05       # femtoliters
DIVISION_MASS_THRESHOLD = 21.0  # 2x initial dry mass


class GrowthModule:
    """Growth and division module."""

    def __init__(self, stochastic: bool = False):
        self._stochastic = stochastic

    def step(self, state: CellState, dt: float) -> bool:
        """Execute one growth timestep. Returns True if division occurred."""
        total_protein = float(state.protein_counts.sum())
        protein_mass = total_protein * 0.0664e-3  # fg
        current_dry_mass = protein_mass / 0.55

        previous_mass = state.dry_mass if state.dry_mass > 0 else current_dry_mass
        state.dry_mass = current_dry_mass

        if previous_mass > 0 and dt > 0:
            state.growth_rate = math.log(state.dry_mass / previous_mass) / dt

        state.volume = INITIAL_VOLUME * (state.dry_mass / INITIAL_DRY_MASS)
        state.volume = max(state.volume, INITIAL_VOLUME * 0.5)

        state.mass_accumulated = state.dry_mass

        threshold = DIVISION_MASS_THRESHOLD
        if self._stochastic:
            threshold *= state.rng.lognormal(0, 0.05)

        if state.dry_mass >= threshold:
            self._divide(state)
            return True
        return False

    def _divide(self, state: CellState) -> None:
        """Cell division: halve macromolecule counts and mass."""
        state.division_count += 1
        state.generation += 1

        if self._stochastic:
            state.protein_counts = state.rng.binomial(
                state.protein_counts.astype(np.int64).clip(0), 0.5
            ).astype(np.float64)
            state.mrna_counts = state.rng.binomial(
                state.mrna_counts.astype(np.int64).clip(0), 0.5
            ).astype(np.float64)
        else:
            state.protein_counts *= 0.5
            state.mrna_counts *= 0.5

        state.dry_mass *= 0.5
        state.volume *= 0.5
        state.mass_accumulated = 0.0
