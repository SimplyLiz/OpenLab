"""DNA replication process — ODE-based (PRD §5)."""

from __future__ import annotations

from typing import Any

from openlab.cellforge.core.process import CellForgeProcess, ProcessPorts, Port
from openlab.cellforge.core.stochastic import michaelis_menten


# E. coli-like parameters
_REPLICATION_SPEED = 1000  # bp/s per fork
_GENOME_LENGTH = 4_600_000  # bp (E. coli)
_KM_DNTP = 0.1  # mM half-saturation for dNTPs
_DNTP_PER_BP = 1e-8  # mM consumed per bp replicated (simplified)
_INITIATION_MASS = 1800.0  # fg cell mass threshold to initiate replication


class Replication(CellForgeProcess):
    """ODE-based DNA replication process.

    Replication initiates when cell mass exceeds a threshold.
    Progress advances linearly based on dNTP availability.
    Two replication forks move bidirectionally from oriC.
    """

    name = "replication"
    algorithm = "ode_rk45"
    preferred_dt = 1.0

    def __init__(self, genome_length: int = _GENOME_LENGTH) -> None:
        self.genome_length = genome_length
        # Time to replicate at max speed (two forks)
        self.min_replication_time = genome_length / (2 * _REPLICATION_SPEED)

    def ports(self) -> ProcessPorts:
        return ProcessPorts(
            inputs=[
                Port(name="dntp_concentrations", dtype="float64"),
                Port(name="replisome_state", dtype="float64"),
            ],
            outputs=[
                Port(name="replication_progress", dtype="float64"),
                Port(name="dntp_updates", dtype="float64"),
            ],
        )

    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        progress = state.get("replication_progress", 0.0)
        replisome = state.get("replisome_state", 0.0)
        cell_mass = state.get("cell_mass", 1000.0)
        dntp = state.get("dntp_concentrations", {})

        dntp_deltas: dict[str, float] = {}

        # Initiate replication if mass threshold exceeded and not already replicating
        if replisome < 0.5 and cell_mass >= _INITIATION_MASS:
            replisome = 1.0

        # Advance replication if active
        if replisome >= 0.5 and progress < 1.0:
            # dNTP saturation
            avg_dntp = sum(dntp.get(n, 0.5) for n in ("datp", "dgtp", "dctp", "dttp")) / 4.0
            dntp_sat = michaelis_menten(avg_dntp, 1.0, _KM_DNTP)

            # Progress increment
            d_progress = (dt / self.min_replication_time) * dntp_sat
            progress = min(1.0, progress + d_progress)

            # dNTP consumption
            bp_replicated = d_progress * self.genome_length
            consumed = bp_replicated * _DNTP_PER_BP
            for n in ("datp", "dgtp", "dctp", "dttp"):
                dntp_deltas[n] = -consumed / 4.0

        return {
            "replication_progress": progress,
            "replisome_state": replisome,
            "dntp_updates": dntp_deltas,
        }
