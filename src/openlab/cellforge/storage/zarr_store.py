"""Zarr-based time-series storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ZarrStore:
    """Stores simulation time-series data in Zarr format."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write_step(self, time: float, state: dict[str, Any]) -> None:
        """Write a single time step to the store."""
        raise NotImplementedError("ZarrStore.write_step not yet implemented")

    def read_variable(self, name: str, time_range: tuple[float, float] | None = None) -> Any:
        """Read a variable's time series."""
        raise NotImplementedError("ZarrStore.read_variable not yet implemented")
