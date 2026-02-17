"""gapseq metabolic reconstruction runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class GapseqRunner:
    """Runs gapseq for metabolic model reconstruction."""

    def __init__(self) -> None:
        pass

    async def run(self, fasta_path: Path, output_dir: Path) -> dict[str, Any]:
        """Run gapseq metabolic reconstruction."""
        raise NotImplementedError("GapseqRunner.run not yet implemented")
