"""Translation process — stochastic protein synthesis (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port
from openlab.cellforge.core.stochastic import michaelis_menten, poisson


# E. coli-like parameters
_K_TRANSLATION = 0.004   # proteins/s per mRNA at saturation
_KM_RIBOSOME = 5000.0    # ribosome half-saturation (molecules)
_KM_AA = 0.2             # amino acid half-saturation (mM)
_AA_PER_PROTEIN = 0.0005 # mM amino acids consumed per protein (simplified)
_GTP_PER_PROTEIN = 0.0002  # mM GTP consumed per protein


class Translation(CellForgeProcess):
    """Stochastic translation using Poisson sampling.

    Rate per mRNA = k * mrna_count * ribosome_saturation * aa_saturation.
    New proteins are sampled from Poisson(rate * dt).
    """

    name = "translation"
    algorithm = "gillespie"
    preferred_dt = 0.1

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="mrna_counts", dtype="int64"),
                Port(name="ribosome_count", dtype="int64"),
                Port(name="aa_concentrations", dtype="float64"),
            ],
            outputs=[
                Port(name="protein_counts", dtype="int64"),
                Port(name="aa_updates", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        mrna_counts = state.get("mrna_counts", {})
        ribosomes = state.get("ribosome_count", 15000)
        aa_conc = state.get("aa_concentrations", {})

        # Ribosome saturation
        ribo_sat = michaelis_menten(ribosomes, 1.0, _KM_RIBOSOME)

        # Average amino acid saturation
        aa_vals = list(aa_conc.values()) if aa_conc else [1.0]
        avg_aa = sum(aa_vals) / len(aa_vals) if aa_vals else 1.0
        aa_sat = michaelis_menten(avg_aa, 1.0, _KM_AA)

        protein_deltas: dict[str, int] = {}
        total_aa_used = 0.0

        for gene_id, count in mrna_counts.items():
            if count <= 0:
                continue
            rate = _K_TRANSLATION * count * ribo_sat * aa_sat
            new_proteins = poisson(rate * dt)
            if new_proteins > 0:
                protein_deltas[gene_id] = new_proteins
                total_aa_used += new_proteins * _AA_PER_PROTEIN

        # Distribute amino acid consumption across all species
        aa_deltas: dict[str, float] = {}
        if aa_conc:
            per_aa = total_aa_used / max(1, len(aa_conc))
            for aa_id in aa_conc:
                aa_deltas[aa_id] = -per_aa

        return {
            "protein_counts": protein_deltas,
            "aa_updates": aa_deltas,
        }
