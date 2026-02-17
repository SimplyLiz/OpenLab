"""Simulation state checkpoint snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class StateSnapshots:
    """Manages simulation state checkpoints."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def save(self, state: dict[str, Any], time: float) -> Path:
        """Save a state snapshot."""
        raise NotImplementedError("StateSnapshots.save not yet implemented")

    def load(self, path: str | Path) -> dict[str, Any]:
        """Load a state snapshot."""
        raise NotImplementedError("StateSnapshots.load not yet implemented")

    def list_snapshots(self) -> list[Path]:
        """List all available snapshots."""
        raise NotImplementedError("StateSnapshots.list_snapshots not yet implemented")
