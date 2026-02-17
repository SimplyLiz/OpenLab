"""Parquet-based tabular storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ParquetStore:
    """Stores simulation summary data in Parquet format."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write(self, data: dict[str, Any]) -> None:
        """Write data to Parquet."""
        raise NotImplementedError("ParquetStore.write not yet implemented")

    def read(self) -> Any:
        """Read Parquet data."""
        raise NotImplementedError("ParquetStore.read not yet implemented")
