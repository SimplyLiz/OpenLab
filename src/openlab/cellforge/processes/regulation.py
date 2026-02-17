"""Gene regulation process (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port
from openlab.cellforge.core.stochastic import hill


# Default parameters
_HILL_K = 0.5   # TF concentration for half-max activation (mM)
_HILL_N = 2.0   # Hill coefficient (cooperativity)
_BASAL_ACTIVITY = 0.1  # minimum promoter activity when not regulated


class Regulation(CellForgeProcess):
    """Transcription factor-mediated gene regulation using Hill functions.

    Each gene's promoter activity is modulated by TF concentrations
    and metabolite signals. Without explicit regulatory network data,
    uses a simplified model where all genes have basal activity
    modulated by global metabolic state.
    """

    name = "regulation"
    algorithm = "event_driven"
    preferred_dt = 1.0

    def __init__(self, knowledge_base: object | None = None) -> None:
        self.kb = knowledge_base
        self._regulatory_map: dict[str, list[str]] = {}
        # Build simple regulatory map from KB transcription units
        if knowledge_base and hasattr(knowledge_base, "transcription_units"):
            for tu in knowledge_base.transcription_units:
                for gene_id in tu.gene_ids:
                    self._regulatory_map[gene_id] = tu.gene_ids

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="tf_concentrations", dtype="float64"),
                Port(name="metabolite_concentrations", dtype="float64"),
            ],
            outputs=[
                Port(name="gene_states", dtype="int64"),
                Port(name="promoter_activities", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        gene_states = dict(state.get("gene_states", {}))
        met_conc = state.get("metabolite_concentrations", {})
        tf_conc = state.get("tf_concentrations", {})

        promoter_activities: dict[str, float] = {}

        # Global metabolic signal: ATP level indicates cellular health
        atp = met_conc.get("atp", 5.0)
        global_signal = hill(atp, 2.0, 2.0)

        for gene_id in gene_states:
            # Basal activity modulated by global metabolic state
            activity = _BASAL_ACTIVITY + (1.0 - _BASAL_ACTIVITY) * global_signal

            # TF-specific regulation if we have TF data
            if tf_conc:
                # Simple model: each TF activates proportionally
                for tf_id, tf_level in tf_conc.items():
                    tf_effect = hill(tf_level, _HILL_K, _HILL_N)
                    activity = max(activity, tf_effect)

            activity = min(1.0, activity)
            promoter_activities[gene_id] = activity

            # Gene is ON if activity > threshold
            gene_states[gene_id] = 1 if activity > 0.05 else 0

        return {
            "gene_states": gene_states,
            "promoter_activities": promoter_activities,
        }
