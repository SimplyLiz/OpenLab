"""Thermodynamic constraints for reaction feasibility."""

from __future__ import annotations

from openlab.cellforge.core.knowledge_base import Reaction


class ThermodynamicConstraints:
    """Applies thermodynamic constraints to metabolic reactions."""

    def __init__(self) -> None:
        pass

    def check_feasibility(self, reaction: Reaction, concentrations: dict[str, float]) -> bool:
        """Check if a reaction is thermodynamically feasible."""
        raise NotImplementedError("ThermodynamicConstraints.check_feasibility not yet implemented")

    def compute_delta_g(self, reaction: Reaction, concentrations: dict[str, float]) -> float:
        """Compute the Gibbs free energy change for a reaction."""
        raise NotImplementedError("ThermodynamicConstraints.compute_delta_g not yet implemented")
