"""Cell division process — event-driven (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port


_DIVISION_MASS_RATIO = 2.0  # divide when mass doubles


class Division(CellForgeProcess):
    """Event-driven cell division.

    Triggers when replication is complete (progress >= 1.0) and
    cell mass has approximately doubled. On division, all extensive
    quantities are halved and replication state is reset.
    """

    name = "division"
    algorithm = "event_driven"
    preferred_dt = 1.0

    def __init__(self, initial_mass: float = 1000.0) -> None:
        self.initial_mass = initial_mass

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="cell_mass", dtype="float64"),
                Port(name="replication_progress", dtype="float64"),
                Port(name="chromosome_count", dtype="int64"),
            ],
            outputs=[
                Port(name="division_event", dtype="bool"),
                Port(name="daughter_state", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        cell_mass = state.get("cell_mass", 1000.0)
        progress = state.get("replication_progress", 0.0)
        chromosomes = state.get("chromosome_count", 1)

        should_divide = (
            progress >= 1.0
            and cell_mass >= self.initial_mass * _DIVISION_MASS_RATIO * 0.9
        )

        if not should_divide:
            return {"division_event": False, "daughter_state": None}

        # Division: halve extensive quantities
        new_mass = cell_mass / 2.0
        daughter = {
            "cell_mass": new_mass,
            "replication_progress": 0.0,
            "replisome_state": 0.0,
            "chromosome_count": chromosomes,
        }

        return {
            "division_event": True,
            "daughter_state": daughter,
            "cell_mass": new_mass,
            "replication_progress": 0.0,
            "replisome_state": 0.0,
        }
