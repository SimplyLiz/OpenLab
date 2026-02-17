"""AI-assisted metabolic gap filling."""

from __future__ import annotations

from openlab.cellforge.core.knowledge_base import KnowledgeBase


class GapFiller:
    """Uses ML models to fill gaps in metabolic reconstructions."""

    def __init__(self) -> None:
        pass

    def fill_gaps(self, kb: KnowledgeBase) -> KnowledgeBase:
        """Identify and fill gaps in the metabolic network."""
        raise NotImplementedError("GapFiller.fill_gaps not yet implemented")
