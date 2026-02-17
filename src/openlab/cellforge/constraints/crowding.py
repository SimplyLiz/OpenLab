"""Macromolecular crowding constraints."""

from __future__ import annotations


class CrowdingConstraints:
    """Models macromolecular crowding effects on reaction rates."""

    def __init__(self, cell_volume: float = 1e-15) -> None:
        self.cell_volume = cell_volume

    def crowding_factor(self, total_protein_mass: float) -> float:
        """Compute the crowding correction factor."""
        raise NotImplementedError("CrowdingConstraints.crowding_factor not yet implemented")
