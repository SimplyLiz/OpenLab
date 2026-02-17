"""2D nutrient diffusion on a toroidal grid.

Discrete Laplacian diffusion with edge replenishment to simulate
fresh media inflow at plate boundaries.
"""
from __future__ import annotations

import numpy as np


def diffuse_2d(field: np.ndarray, rate: float, dt: float) -> np.ndarray:
    """Discrete Laplacian diffusion on a 2D toroidal grid."""
    laplacian = (
        np.roll(field, 1, 0) + np.roll(field, -1, 0)
        + np.roll(field, 1, 1) + np.roll(field, -1, 1)
        - 4 * field
    )
    return np.clip(field + rate * dt * laplacian, 0, None)


def replenish_edges(
    field: np.ndarray, base_conc: float, rate: float
) -> np.ndarray:
    """Replenish nutrients at grid edges (simulates fresh media inflow)."""
    field[0, :] += (base_conc - field[0, :]) * rate
    field[-1, :] += (base_conc - field[-1, :]) * rate
    field[:, 0] += (base_conc - field[:, 0]) * rate
    field[:, -1] += (base_conc - field[:, -1]) * rate
    return field
