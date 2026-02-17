"""Base process interface (PRD §4.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class Port(BaseModel):
    """A named connection point for state variables."""

    name: str
    dtype: str = "float64"
    shape: tuple[int, ...] | None = None
    description: str = ""


class ProcessPorts(BaseModel):
    """Declares the inputs and outputs of a process."""

    inputs: list[Port] = []
    outputs: list[Port] = []


class CellForgeProcess(ABC):
    """Abstract base class for all biological processes (PRD §4.1).

    Each process reads from input ports, computes updates, and writes
    to output ports. The coordinator calls step() with the current
    simulation state.
    """

    name: str = "unnamed"
    algorithm: str = "unknown"
    preferred_dt: float = 1.0

    @abstractmethod
    def ports(self) -> ProcessPorts:
        """Declare the state variables this process reads and writes."""
        ...

    @abstractmethod
    def step(self, state: dict[str, Any], dt: float) -> dict[str, Any]:
        """Advance the process by dt, returning state updates.

        Args:
            state: Current simulation state (read-only view).
            dt: Time step in seconds.

        Returns:
            Dictionary of state variable updates.
        """
        ...

    def initialize(self, state: dict[str, Any]) -> None:
        """Optional one-time setup before simulation starts."""

    def finalize(self, state: dict[str, Any]) -> None:
        """Optional cleanup after simulation ends."""
