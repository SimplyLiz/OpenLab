"""Cell maintenance and housekeeping process (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port


# E. coli non-growth-associated maintenance: ~8.4 mmol ATP/gDW/h
# Converted: 8.4 / 3600 ≈ 0.0023 mmol/gDW/s
# For a 1000 fg cell (~1e-12 g): 0.0023 * 1e-12 ≈ 2.3e-15 mmol/s
# In our concentration units (mM): ~0.001 mM/s
_MAINTENANCE_RATE = 0.001  # mM ATP consumed per second per unit mass (1000 fg)


class Maintenance(CellForgeProcess):
    """ATP maintenance, chaperone activity, and housekeeping.

    Consumes ATP proportional to cell mass to represent the
    non-growth-associated maintenance energy requirement.
    """

    name = "maintenance"
    algorithm = "ode_rk45"
    preferred_dt = 1.0

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="atp_concentration", dtype="float64"),
                Port(name="cell_mass", dtype="float64"),
            ],
            outputs=[
                Port(name="atp_consumption", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        atp = state.get("metabolite_concentrations", {}).get("atp", 5.0)
        cell_mass = state.get("cell_mass", 1000.0)

        # ATP consumed this step
        consumption = _MAINTENANCE_RATE * (cell_mass / 1000.0) * dt

        # Don't consume more ATP than available
        consumption = min(consumption, max(0, atp))

        return {
            "atp_consumption": consumption,
        }
