"""FANTASIA integration for functional annotation."""

from __future__ import annotations


class FantasiaAnnotator:
    """FANTASIA-based functional annotation transfer."""

    def __init__(self) -> None:
        pass

    def annotate(self, sequences: list[str]) -> list[dict[str, str]]:
        """Annotate protein sequences using FANTASIA."""
        raise NotImplementedError("FantasiaAnnotator.annotate not yet implemented")
