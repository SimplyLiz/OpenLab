"""External database access (KEGG, BiGG, UniProt, etc.)."""

from __future__ import annotations

from typing import Any


class DatabaseClient:
    """Unified client for querying biological databases."""

    def __init__(self) -> None:
        pass

    async def query_kegg(self, query: str) -> list[dict[str, Any]]:
        """Query the KEGG database."""
        raise NotImplementedError("DatabaseClient.query_kegg not yet implemented")

    async def query_bigg(self, query: str) -> list[dict[str, Any]]:
        """Query the BiGG Models database."""
        raise NotImplementedError("DatabaseClient.query_bigg not yet implemented")

    async def query_uniprot(self, query: str) -> list[dict[str, Any]]:
        """Query UniProt."""
        raise NotImplementedError("DatabaseClient.query_uniprot not yet implemented")
