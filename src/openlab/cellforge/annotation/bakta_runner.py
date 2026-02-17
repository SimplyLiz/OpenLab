"""Bakta gene annotation runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class BaktaRunner:
    """Runs Bakta for prokaryotic gene calling and annotation."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else None

    async def run(self, fasta_path: Path, output_dir: Path) -> dict[str, Any]:
        """Run Bakta annotation on a genome FASTA."""
        raise NotImplementedError("BaktaRunner.run not yet implemented")
