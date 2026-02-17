"""Epigenetics module for stochastic simulation.

Models methylation-based gene regulation in response to nutrient stress.
Under glucose depletion, metabolism genes are demethylated (upregulated)
while non-essential gene expression genes are methylated (silenced).
"""
from __future__ import annotations

from openlab.models import CellSpecGene
from openlab.simulation.state import CellState


class EpigeneticsModule:
    """Methylation-based epigenetic regulation responding to environment."""

    NUTRIENT_STRESS_THRESHOLD = 0.3  # mM glucose
    METHYLATION_RATE = 0.001
    DEMETHYLATION_RATE = 0.0005

    def step(self, state: CellState, genes: list[CellSpecGene]) -> None:
        """Update methylation levels based on nutrient state."""
        glucose = state.get_metabolite("glucose")
        stressed = glucose < self.NUTRIENT_STRESS_THRESHOLD

        for i, gene in enumerate(genes):
            if stressed:
                if gene.classification == "metabolism":
                    # Upregulate metabolism under stress
                    state.methylation[i] = max(
                        0.0, state.methylation[i] - self.DEMETHYLATION_RATE
                    )
                elif (
                    gene.classification == "gene_expression"
                    and not gene.is_essential
                ):
                    # Silence non-essential expression machinery
                    state.methylation[i] = min(
                        1.0, state.methylation[i] + self.METHYLATION_RATE
                    )
            else:
                # Slow return to baseline when not stressed
                state.methylation[i] *= 0.999
