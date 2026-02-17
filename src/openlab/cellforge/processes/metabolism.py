"""Metabolism process — simplified Michaelis-Menten kinetics (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port
from openlab.cellforge.core.stochastic import michaelis_menten


# Kinetic parameters (E. coli-like)
_VMAX_GLUCOSE = 10.0   # mmol/gDW/h max glucose uptake
_KM_GLUCOSE = 0.05     # mM
_ATP_YIELD = 18.0      # mol ATP per mol glucose (glycolysis + TCA + oxphos, simplified)
_GROWTH_MU_MAX = 0.0005  # 1/s (~23 min doubling)
_KM_ATP_GROWTH = 1.0   # mM
_MAINTENANCE_ATP = 0.0008  # mM/s per unit mass


class Metabolism(CellForgeProcess):
    """Simplified Michaelis-Menten metabolism process.

    Without a COBRA model, uses Michaelis-Menten kinetics for glucose
    uptake, ATP production via central carbon metabolism, and growth.
    """

    name = "metabolism"
    algorithm = "fba"
    preferred_dt = 1.0

    def __init__(self, knowledge_base: object | None = None) -> None:
        self.kb = knowledge_base
        self._reactions: list = []
        if knowledge_base and hasattr(knowledge_base, "reactions"):
            self._reactions = knowledge_base.reactions

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="metabolite_concentrations", dtype="float64"),
                Port(name="enzyme_concentrations", dtype="float64"),
            ],
            outputs=[
                Port(name="flux_distribution", dtype="float64"),
                Port(name="metabolite_updates", dtype="float64"),
                Port(name="growth_rate", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        met = state.get("metabolite_concentrations", {})
        cell_mass = state.get("cell_mass", 1000.0)
        flux: dict[str, float] = {}
        deltas: dict[str, float] = {}

        # --- Glucose uptake ---
        glc = met.get("glucose", met.get("glc", 0.0))
        glc_uptake = michaelis_menten(glc, _VMAX_GLUCOSE, _KM_GLUCOSE)
        flux["glucose_uptake"] = glc_uptake

        glc_consumed = glc_uptake * dt / 3600.0
        glc_key = "glucose" if "glucose" in met else "glc"
        deltas[glc_key] = -glc_consumed

        # --- ATP production from glucose catabolism ---
        atp_produced = glc_consumed * _ATP_YIELD
        flux["atp_synthase"] = atp_produced / dt * 3600.0 if dt > 0 else 0

        # --- ATP maintenance cost ---
        atp_maintenance = _MAINTENANCE_ATP * (cell_mass / 1000.0) * dt

        deltas["atp"] = atp_produced - atp_maintenance
        deltas["adp"] = -atp_produced + atp_maintenance

        # --- Pyruvate as intermediate ---
        deltas["pyruvate"] = glc_consumed * 2.0 - glc_consumed * 1.8  # net small accumulation
        deltas["nadh"] = glc_consumed * 4.0
        deltas["nad"] = -glc_consumed * 4.0

        # --- KB-defined reactions (simplified) ---
        for rxn in self._reactions:
            sub_factor = 1.0
            for met_id in rxn.reactants:
                sub_factor *= michaelis_menten(met.get(met_id, 0.0), 1.0, 0.1)
            f = _VMAX_GLUCOSE * 0.5 * sub_factor
            f = max(rxn.lower_bound, min(rxn.upper_bound, f))
            flux[rxn.id] = f
            for mid, coeff in rxn.reactants.items():
                deltas[mid] = deltas.get(mid, 0.0) - coeff * f * dt / 3600.0
            for mid, coeff in rxn.products.items():
                deltas[mid] = deltas.get(mid, 0.0) + coeff * f * dt / 3600.0

        # --- Growth rate ---
        atp_now = met.get("atp", 5.0) + deltas.get("atp", 0.0)
        growth_rate = michaelis_menten(max(0, atp_now), _GROWTH_MU_MAX, _KM_ATP_GROWTH)
        mass_increase = growth_rate * cell_mass * dt

        return {
            "flux_distribution": flux,
            "metabolite_updates": deltas,
            "growth_rate": growth_rate,
            "cell_mass": cell_mass + mass_increase,
        }
