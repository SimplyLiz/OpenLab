"""Cross-database identifier mapping."""

from __future__ import annotations


class IDMapper:
    """Maps identifiers across biological databases."""

    def __init__(self) -> None:
        pass

    def map_ids(self, ids: list[str], source_db: str, target_db: str) -> dict[str, str | None]:
        """Map a list of IDs from one database to another.

        Args:
            ids: List of identifiers to map.
            source_db: Source database (e.g., "kegg", "bigg", "uniprot").
            target_db: Target database.

        Returns:
            Mapping of source ID -> target ID (None if not found).
        """
        raise NotImplementedError("IDMapper.map_ids not yet implemented")
