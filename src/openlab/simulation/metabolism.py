"""Metabolism simulation module.

Computes Michaelis-Menten reaction rates and updates metabolite concentrations.
Runs at fast timestep (default 0.5s).
"""
from __future__ import annotations

import math

import numpy as np

from openlab.models import CellSpecReaction
from openlab.simulation.state import CellState


class MetabolismModule:
    """Metabolism module using Michaelis-Menten kinetics."""

    def __init__(self, reactions: list[CellSpecReaction]):
        self._reactions = reactions

    def step(self, state: CellState, dt: float) -> None:
        """Execute one metabolism timestep."""
        for rxn in self._reactions:
            rate = self._compute_rate(rxn, state)
            if not math.isfinite(rate) or rate <= 0:
                continue

            # Flux limit: cap rate so no substrate goes negative
            for sub in rxn.substrates:
                idx = state.metabolite_index.get(sub.metabolite_id)
                if idx is not None:
                    available = state.metabolite_concentrations[idx]
                    demand = rate * abs(sub.coefficient) * dt
                    if demand > available and demand > 0:
                        rate = available / (abs(sub.coefficient) * dt) * 0.95

            if rate <= 0:
                continue

            # Apply stoichiometric changes
            for sub in rxn.substrates:
                idx = state.metabolite_index.get(sub.metabolite_id)
                if idx is not None:
                    state.metabolite_concentrations[idx] -= rate * abs(sub.coefficient) * dt

            for prod in rxn.products:
                idx = state.metabolite_index.get(prod.metabolite_id)
                if idx is not None:
                    state.metabolite_concentrations[idx] += rate * abs(prod.coefficient) * dt

        # Clamp negative concentrations to zero
        np.clip(state.metabolite_concentrations, 0.0, None, out=state.metabolite_concentrations)

    def _compute_rate(self, rxn: CellSpecReaction, state: CellState) -> float:
        """Compute Michaelis-Menten rate for a reaction."""
        if rxn.kinetics is None or rxn.kinetics.kcat is None:
            return 0.0

        kcat = rxn.kinetics.kcat.value

        # Get enzyme concentration (sum of gene products)
        if not rxn.gene_locus_tags:
            rate = kcat
        else:
            enzyme_conc = 0.0
            for locus_tag in rxn.gene_locus_tags:
                enzyme_conc += state.get_protein(locus_tag)
            if enzyme_conc <= 0:
                return 0.0

            volume_l = state.volume * 1e-15
            enzyme_conc_mm = enzyme_conc / (6.022e23 * volume_l) * 1e3
            rate = kcat * enzyme_conc_mm

        # Substrate saturation terms
        for sub in rxn.substrates:
            sub_conc = state.get_metabolite(sub.metabolite_id)
            km_pv = rxn.kinetics.km.get(sub.metabolite_id)
            km = km_pv.value if km_pv else 0.1

            if km + sub_conc > 0:
                rate *= sub_conc / (km + sub_conc)
            else:
                rate = 0.0

        # Competitive inhibition
        for met_id, ki_pv in rxn.kinetics.ki.items():
            inh_conc = state.get_metabolite(met_id)
            ki = ki_pv.value
            if ki > 0:
                rate *= ki / (ki + inh_conc)

        # Thermodynamic feasibility check
        if (
            rxn.kinetics.delta_g is not None
            and rxn.kinetics.delta_g.value > 0
            and not rxn.kinetics.reversible
        ):
            dg = rxn.kinetics.delta_g.value
            therm_factor = math.exp(-dg / (8.314e-3 * 310))
            rate *= max(0.0, min(1.0, therm_factor))

        return max(0.0, rate)
