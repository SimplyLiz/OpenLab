"""Transcription process — stochastic mRNA synthesis (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port
from openlab.cellforge.core.stochastic import michaelis_menten, poisson


# E. coli-like parameters
_K_TRANSCRIPTION = 0.008  # base rate (mRNAs/s per active gene at saturation)
_KM_RNAP = 500.0          # RNAP half-saturation (molecules)
_KM_NTP = 0.3             # NTP half-saturation (mM)
_NTP_PER_MRNA = 0.001     # mM NTP consumed per mRNA produced (simplified)


class Transcription(CellForgeProcess):
    """Stochastic transcription using Poisson sampling.

    Rate per gene = k * gene_state * promoter_activity * rnap_saturation * ntp_saturation.
    New mRNAs are sampled from Poisson(rate * dt).
    """

    name = "transcription"
    algorithm = "gillespie"
    preferred_dt = 0.1

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="gene_states", dtype="int64"),
                Port(name="rnap_count", dtype="int64"),
                Port(name="ntp_concentrations", dtype="float64"),
            ],
            outputs=[
                Port(name="mrna_counts", dtype="int64"),
                Port(name="ntp_updates", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        gene_states = state.get("gene_states", {})
        promoter_activities = state.get("promoter_activities", {})
        rnap = state.get("rnap_count", 2000)
        ntp = state.get("ntp_concentrations", {})

        # RNAP saturation
        rnap_sat = michaelis_menten(rnap, 1.0, _KM_RNAP)

        # Average NTP saturation
        ntp_vals = [ntp.get(n, 1.0) for n in ("atp", "gtp", "ctp", "utp")]
        ntp_sat = 1.0
        for v in ntp_vals:
            ntp_sat *= michaelis_menten(v, 1.0, _KM_NTP)

        mrna_deltas: dict[str, int] = {}
        total_ntps_used = 0.0

        for gene_id, active in gene_states.items():
            if not active:
                continue
            promoter = promoter_activities.get(gene_id, 1.0)
            rate = _K_TRANSCRIPTION * promoter * rnap_sat * ntp_sat
            new_mrnas = poisson(rate * dt)
            if new_mrnas > 0:
                mrna_deltas[gene_id] = new_mrnas
                total_ntps_used += new_mrnas * _NTP_PER_MRNA

        # Distribute NTP consumption evenly across species
        ntp_deltas: dict[str, float] = {}
        per_species = total_ntps_used / 4.0
        for n in ("atp", "gtp", "ctp", "utp"):
            ntp_deltas[n] = -per_species

        return {
            "mrna_counts": mrna_deltas,
            "ntp_updates": ntp_deltas,
        }
