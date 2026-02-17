"""Membrane transport process (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port
from openlab.cellforge.core.stochastic import michaelis_menten


# E. coli-like parameters
_VMAX_TRANSPORT = 0.01   # mM/s max uptake rate per transporter unit
_KM_TRANSPORT = 0.1      # mM half-saturation for external substrate
_DEFAULT_TRANSPORTERS = 100  # default transporter count if not in state


class Transport(CellForgeProcess):
    """Michaelis-Menten membrane transport for nutrient uptake and secretion.

    Uptake rate depends on external substrate concentration and
    transporter abundance. Nutrients flow down their concentration
    gradient.
    """

    name = "transport"
    algorithm = "ode_rk45"
    preferred_dt = 1.0

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="external_metabolites", dtype="float64"),
                Port(name="internal_metabolites", dtype="float64"),
                Port(name="transporter_counts", dtype="int64"),
            ],
            outputs=[
                Port(name="metabolite_flux", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        external = state.get("external_metabolites", {})
        internal = state.get("metabolite_concentrations", {})
        transporters = state.get("transporter_counts", {})

        flux: dict[str, float] = {}
        met_updates: dict[str, float] = {}

        for met_id, ext_conc in external.items():
            int_conc = internal.get(met_id, 0.0)

            # Net uptake: positive = import, negative = export
            n_trans = transporters.get(met_id, _DEFAULT_TRANSPORTERS)
            trans_factor = n_trans / _DEFAULT_TRANSPORTERS

            # Uptake rate (Michaelis-Menten on external concentration)
            uptake = michaelis_menten(ext_conc, _VMAX_TRANSPORT * trans_factor, _KM_TRANSPORT)

            # Reduce uptake if internal is already high (feedback inhibition)
            if int_conc > ext_conc * 0.8:
                uptake *= 0.1

            uptake_amount = uptake * dt

            flux[met_id] = uptake
            met_updates[met_id] = uptake_amount

        return {
            "metabolite_flux": flux,
            "metabolite_updates": met_updates,
        }
