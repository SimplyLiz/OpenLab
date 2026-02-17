"""Macromolecule degradation process (PRD §5)."""

from __future__ import annotations

import math
from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port
from openlab.cellforge.core.stochastic import poisson


# E. coli-like parameters
_MRNA_HALF_LIFE = 300.0     # seconds (5 min)
_PROTEIN_HALF_LIFE = 36000.0  # seconds (10 hours)


class Degradation(CellForgeProcess):
    """First-order degradation of mRNA and proteins.

    Each molecule is degraded with probability k_deg * dt per timestep,
    where k_deg = ln(2) / half_life. The number degraded is sampled
    from Poisson(count * k_deg * dt).
    """

    name = "degradation"
    algorithm = "gillespie"
    preferred_dt = 0.1

    def __init__(
        self,
        mrna_half_life: float = _MRNA_HALF_LIFE,
        protein_half_life: float = _PROTEIN_HALF_LIFE,
    ) -> None:
        self.k_deg_mrna = math.log(2) / mrna_half_life
        self.k_deg_protein = math.log(2) / protein_half_life

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="mrna_counts", dtype="int64"),
                Port(name="protein_counts", dtype="int64"),
            ],
            outputs=[
                Port(name="mrna_updates", dtype="int64"),
                Port(name="protein_updates", dtype="int64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        mrna_counts = state.get("mrna_counts", {})
        protein_counts = state.get("protein_counts", {})

        mrna_deltas: dict[str, int] = {}
        protein_deltas: dict[str, int] = {}

        for gene_id, count in mrna_counts.items():
            if count <= 0:
                continue
            degraded = poisson(count * self.k_deg_mrna * dt)
            degraded = min(degraded, count)
            if degraded > 0:
                mrna_deltas[gene_id] = -degraded

        for gene_id, count in protein_counts.items():
            if count <= 0:
                continue
            degraded = poisson(count * self.k_deg_protein * dt)
            degraded = min(degraded, count)
            if degraded > 0:
                protein_deltas[gene_id] = -degraded

        return {
            "mrna_updates": mrna_deltas,
            "protein_updates": protein_deltas,
        }
