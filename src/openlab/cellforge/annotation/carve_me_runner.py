"""CarveMe metabolic reconstruction runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class CarveMeRunner:
    """Runs CarveMe for metabolic model reconstruction."""

    def __init__(self) -> None:
        pass

    async def run(self, protein_fasta: Path, output_dir: Path) -> dict[str, Any]:
        """Run CarveMe metabolic reconstruction."""
        raise NotImplementedError("CarveMeRunner.run not yet implemented")
