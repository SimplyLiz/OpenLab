"""Mutation engine for stochastic simulation.

Applies random expression-level mutations on cell division. Log-normal
distribution ensures most mutations are mild with occasional large effects.
"""
from __future__ import annotations

from openlab.models import CellSpecGene
from openlab.simulation.state import CellState


class MutationModule:
    """Applies stochastic mutations to gene expression modifiers on division."""

    def __init__(self, mutation_rate: float = 1e-4):
        self.mutation_rate = mutation_rate

    def apply_division_mutations(
        self, state: CellState, genes: list[CellSpecGene]
    ) -> None:
        """Roll for mutations on each gene after a division event."""
        for i, gene in enumerate(genes):
            if state.rng.random() < self.mutation_rate:
                # Log-normal: mean-neutral, ~15% std dev
                factor = state.rng.lognormal(0, 0.15)
                state.gene_expression_modifiers[i] *= factor
                state.mutations[gene.locus_tag] = float(
                    state.gene_expression_modifiers[i]
                )
