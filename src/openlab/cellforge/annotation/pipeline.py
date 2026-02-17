"""Annotation pipeline (PRD §6.1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openlab.cellforge.core.knowledge_base import KnowledgeBase


class AnnotationPipeline:
    """Orchestrates genome annotation stages (PRD §6.1).

    Stages:
        1. Gene calling (Bakta/Prodigal)
        2. Metabolic reconstruction (gapseq/CarveMe)
        3. AI gap-filling
        4. Reconciliation
        5. Knowledge base assembly
    """

    def __init__(self, fasta_path: str | Path, output_dir: str | Path = "annotation_output") -> None:
        self.fasta_path = Path(fasta_path)
        self.output_dir = Path(output_dir)
        self._results: dict[str, Any] = {}

    async def run(self) -> KnowledgeBase:
        """Run the full annotation pipeline.

        Returns:
            Assembled KnowledgeBase.
        """
        raise NotImplementedError("AnnotationPipeline.run not yet implemented")

    async def run_stage(self, stage: str) -> Any:
        """Run a single annotation stage.

        Args:
            stage: Stage name (e.g., "gene_calling", "metabolic_reconstruction").

        Returns:
            Stage-specific results.
        """
        raise NotImplementedError(f"Stage '{stage}' not yet implemented")
