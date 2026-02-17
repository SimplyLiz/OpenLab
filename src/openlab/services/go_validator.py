"""GO term validation — check GO IDs against the Gene Ontology.

Validates that GO terms extracted by the normalizer are real GO IDs,
preventing hallucinated or malformed terms from entering convergence scoring.

Fail-open: if no data file is found, all terms are accepted.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Module-level cache
_go_ids: frozenset[str] | None = None
_loaded = False


def _load_go_ids() -> frozenset[str]:
    """Load valid GO IDs from data/go_ids.txt or parse from go-basic.obo.

    Returns an empty frozenset if no data file exists (fail-open).
    Cached at module level after first load.
    """
    global _go_ids, _loaded
    if _loaded:
        return _go_ids or frozenset()

    data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
    txt_path = data_dir / "go_ids.txt"
    obo_path = data_dir / "go-basic.obo"

    ids: set[str] = set()

    if txt_path.exists():
        for line in txt_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("GO:"):
                ids.add(line)
        logger.info(f"Loaded {len(ids)} GO IDs from {txt_path}")
    elif obo_path.exists():
        for line in obo_path.read_text().splitlines():
            if line.startswith("id: GO:"):
                ids.add(line[4:].strip())
        logger.info(f"Parsed {len(ids)} GO IDs from {obo_path}")
    else:
        logger.warning(
            "No GO data file found (data/go_ids.txt or data/go-basic.obo). "
            "GO validation disabled (fail-open)."
        )
        _go_ids = None
        _loaded = True
        return frozenset()

    _go_ids = frozenset(ids)
    _loaded = True
    return _go_ids


def is_valid_go_term(go_id: str) -> bool:
    """Check if a GO term ID is valid. Fail-open if no data loaded."""
    ids = _load_go_ids()
    if not ids:
        return True  # fail-open
    return go_id in ids


def validate_go_terms(go_terms: set[str]) -> tuple[set[str], set[str]]:
    """Partition GO terms into (valid, invalid) sets.

    If no data file is loaded, all terms are considered valid (fail-open).
    """
    ids = _load_go_ids()
    if not ids:
        return go_terms, set()

    valid = go_terms & ids
    invalid = go_terms - ids
    return valid, invalid


def reset_go_cache():
    """Reset the cached GO IDs (for testing)."""
    global _go_ids, _loaded
    _go_ids = None
    _loaded = False
