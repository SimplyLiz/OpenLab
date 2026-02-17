"""Batch evidence runner — dispatches named evidence sources against DB genes.

Usage:
    python -m openlab.pipeline.evidence_runner <source>
    python -m openlab.pipeline.evidence_runner --list

Each evidence source module exposes:
    run_<source>(db, genes, http) -> int   (count of evidence rows stored)

Sources are discovered at runtime via the plugin registry (openlab.registry).
Contrib modules like openlab.contrib.dnasyn register themselves on import.
"""

from __future__ import annotations

import logging
import sys

import httpx
from sqlalchemy.orm import Session

from openlab.db.engine import get_session_factory
from openlab.db.models.evidence import Evidence
from openlab.db.models.gene import Gene

logger = logging.getLogger(__name__)


def _ensure_contrib_loaded() -> None:
    """Import contrib modules so they register their sources."""
    try:
        import openlab.contrib.dnasyn  # noqa: F401
    except Exception:
        pass  # optional — may not be installed
    try:
        import openlab.contrib.cancer  # noqa: F401
    except Exception:
        pass  # optional — may not be installed


def list_sources() -> list[dict[str, str]]:
    """List all registered evidence sources with availability status."""
    from openlab.registry import check_source_availability, list_registered_sources

    _ensure_contrib_loaded()
    results = []
    for name, reg in sorted(list_registered_sources().items()):
        status = check_source_availability(name)
        results.append({
            "name": name,
            "module": reg.module_path,
            "status": status,
            "group": reg.group,
            "description": reg.description,
        })
    return results


def has_existing_evidence(db: Session, gene_id: int, source: str) -> bool:
    """Check if evidence already exists for this gene+source (dedup)."""
    return (
        db.query(Evidence)
        .filter(Evidence.gene_id == gene_id, Evidence.source_ref == source)
        .first()
    ) is not None


def load_target_genes(db: Session, unknown_only: bool = True) -> list[Gene]:
    """Load genes that have protein sequences for evidence collection."""
    q = db.query(Gene).filter(Gene.protein_sequence.isnot(None))
    if unknown_only:
        from sqlalchemy import or_
        q = q.filter(
            or_(
                Gene.product.is_(None),
                Gene.product.ilike("%hypothetical%"),
                Gene.product.ilike("%uncharacterized%"),
                Gene.product.ilike("%unknown function%"),
                Gene.product.ilike("%putative%"),
            )
        )
    return q.order_by(Gene.start).all()


def run_source(source: str, unknown_only: bool = True) -> int:
    """Run a single evidence source against all target genes.

    Returns count of new evidence rows stored.
    """
    from openlab.registry import load_runner, list_registered_sources

    _ensure_contrib_loaded()
    registered = list_registered_sources()
    if source not in registered:
        raise ValueError(f"Unknown source: {source}. Available: {sorted(registered)}")

    runner = load_runner(source)

    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        genes = load_target_genes(db, unknown_only=unknown_only)
        if not genes:
            logger.info("No target genes found")
            return 0

        logger.info("Running %s on %d genes", source, len(genes))

        with httpx.Client(timeout=60.0, follow_redirects=True) as http:
            count = runner(db, genes, http)

        logger.info("Source %s stored %d evidence rows", source, count)
        return count


def run_all_sources(unknown_only: bool = True) -> dict[str, int]:
    """Run all available evidence sources. Returns {source: count}."""
    from openlab.registry import list_registered_sources

    _ensure_contrib_loaded()
    results = {}
    for source in list_registered_sources():
        try:
            results[source] = run_source(source, unknown_only=unknown_only)
        except Exception as e:
            logger.error("Source %s failed: %s", source, e)
            results[source] = -1
    return results


def evidence_status() -> dict[str, int]:
    """Count evidence rows per source in the DB."""
    from sqlalchemy import func
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        rows = (
            db.query(Evidence.source_ref, func.count(Evidence.evidence_id))
            .group_by(Evidence.source_ref)
            .all()
        )
        return {source or "unknown": count for source, count in rows}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if len(sys.argv) < 2 or sys.argv[1] == "--list":
        for s in list_sources():
            print(f"  {s['name']:25s} {s['status']:15s} {s.get('group', '')}")
        sys.exit(0)

    if sys.argv[1] == "--status":
        for source, count in sorted(evidence_status().items()):
            print(f"  {source:25s} {count:5d}")
        sys.exit(0)

    source_name = sys.argv[1]
    count = run_source(source_name)
    print(f"Done: {count} evidence rows stored for {source_name}")
