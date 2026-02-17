"""Cell simulation state.

Ported from CellForge's Dart CellState. Uses numpy arrays for metabolite
concentrations, protein counts, and mRNA counts.
"""
from __future__ import annotations

import numpy as np

from openlab.models import CellSpec


class CellState:
    """Complete simulation state at a point in time."""

    def __init__(
        self,
        time: float,
        metabolite_concentrations: np.ndarray,
        protein_counts: np.ndarray,
        mrna_counts: np.ndarray,
        volume: float,
        metabolite_index: dict[str, int],
        gene_index: dict[str, int],
        *,
        dry_mass: float = 0.0,
        growth_rate: float = 0.0,
        mass_accumulated: float = 0.0,
        division_count: int = 0,
        knocked_out_genes: set[str] | None = None,
        rng: np.random.Generator | None = None,
        gene_expression_modifiers: np.ndarray | None = None,
        mutations: dict[str, float] | None = None,
        methylation: np.ndarray | None = None,
        cell_id: int = 0,
        parent_id: int | None = None,
        generation: int = 0,
    ):
        self.time = time
        self.metabolite_concentrations = metabolite_concentrations
        self.protein_counts = protein_counts
        self.mrna_counts = mrna_counts
        self.volume = volume
        self.metabolite_index = metabolite_index
        self.gene_index = gene_index
        self.dry_mass = dry_mass
        self.growth_rate = growth_rate
        self.mass_accumulated = mass_accumulated
        self.division_count = division_count
        self.knocked_out_genes = knocked_out_genes or set()
        self.rng = rng if rng is not None else np.random.default_rng(42)
        n_genes = len(gene_index)
        self.gene_expression_modifiers = (
            gene_expression_modifiers if gene_expression_modifiers is not None
            else np.ones(n_genes, dtype=np.float64)
        )
        self.mutations: dict[str, float] = mutations if mutations is not None else {}
        self.methylation = (
            methylation if methylation is not None
            else np.zeros(n_genes, dtype=np.float64)
        )
        self.cell_id = cell_id
        self.parent_id = parent_id
        self.generation = generation

    @classmethod
    def from_spec(
        cls,
        spec: CellSpec,
        knockouts: set[str] | None = None,
        seed: int = 42,
    ) -> CellState:
        """Create initial state from a CellSpec."""
        knockouts = knockouts or set()

        # Metabolite concentrations
        met_conc = np.zeros(len(spec.metabolites), dtype=np.float64)
        met_index: dict[str, int] = {}
        for i, met in enumerate(spec.metabolites):
            met_index[met.id] = i
            met_conc[i] = met.initial_concentration

        # Protein and mRNA counts
        protein_counts = np.zeros(len(spec.genes), dtype=np.float64)
        mrna_counts = np.zeros(len(spec.genes), dtype=np.float64)
        gene_index: dict[str, int] = {}

        for i, gene in enumerate(spec.genes):
            gene_index[gene.locus_tag] = i
            if gene.locus_tag in knockouts:
                protein_counts[i] = 0.0
                mrna_counts[i] = 0.0
            else:
                protein_counts[i] = 167.0
                mrna_counts[i] = 0.02

        return cls(
            time=0.0,
            metabolite_concentrations=met_conc,
            protein_counts=protein_counts,
            mrna_counts=mrna_counts,
            volume=spec.simulation_parameters.initial_volume,
            metabolite_index=met_index,
            gene_index=gene_index,
            knocked_out_genes=set(knockouts),
            rng=np.random.default_rng(seed),
        )

    def is_knocked_out(self, locus_tag: str) -> bool:
        return locus_tag in self.knocked_out_genes

    def get_metabolite(self, id: str) -> float:
        idx = self.metabolite_index.get(id)
        return float(self.metabolite_concentrations[idx]) if idx is not None else 0.0

    def set_metabolite(self, id: str, value: float) -> None:
        idx = self.metabolite_index.get(id)
        if idx is not None:
            self.metabolite_concentrations[idx] = value

    def get_protein(self, locus_tag: str) -> float:
        idx = self.gene_index.get(locus_tag)
        return float(self.protein_counts[idx]) if idx is not None else 0.0

    @property
    def total_protein_mass(self) -> float:
        """Rough protein mass estimate (avg MW ~40 kDa)."""
        return float(self.protein_counts.sum()) * 40000

    def has_numerical_issue(self) -> bool:
        """Check for NaN or Inf in state arrays."""
        return bool(
            np.any(~np.isfinite(self.metabolite_concentrations))
            or np.any(~np.isfinite(self.protein_counts))
        )

    def snapshot(self) -> dict:
        """Create a snapshot dict for recording."""
        snap = {
            "time": self.time,
            "volume": self.volume,
            "dryMass": self.dry_mass,
            "growthRate": self.growth_rate,
            "divisionCount": self.division_count,
            "totalProtein": float(self.protein_counts.sum()),
            "totalMRNA": float(self.mrna_counts.sum()),
            "cell_id": self.cell_id,
            "generation": self.generation,
            "mutation_count": len(self.mutations),
            "fitness": self.growth_rate,
        }

        for key in ("atp", "adp", "gtp", "glucose", "aa_pool"):
            idx = self.metabolite_index.get(key)
            if idx is not None:
                snap[key] = float(self.metabolite_concentrations[idx])

        if self.knocked_out_genes:
            snap["knockouts"] = sorted(self.knocked_out_genes)

        return snap
