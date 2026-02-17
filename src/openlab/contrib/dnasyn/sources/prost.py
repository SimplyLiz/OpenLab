"""PROST (PROtein Structure-based Transfer) local homology search.

Runs prost subprocess to search a structure database for
remote homologs that sequence-based methods miss.
"""

from __future__ import annotations

import csv
import logging
import subprocess
import tempfile
from io import StringIO
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from openlab.config import config
from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)


def run_prost_single(protein_seq: str, locus_tag: str) -> dict:
    """Run prost search on a single sequence."""
    db_path = config.tools.prost_db_path
    if not db_path:
        return {"source": "prost"}

    with tempfile.TemporaryDirectory() as tmpdir:
        query_path = Path(tmpdir) / "query.fasta"
        query_path.write_text(f">{locus_tag}\n{protein_seq}\n")
        results_path = Path(tmpdir) / "results.tsv"

        try:
            subprocess.run(
                [
                    "prost", "search",
                    "-q", str(query_path),
                    "-d", db_path,
                    "-o", str(results_path),
                ],
                capture_output=True, text=True, timeout=300,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("prost failed for %s: %s", locus_tag, e)
            return {"source": "prost"}

        if not results_path.exists():
            return {"source": "prost"}

        return _parse_tsv(results_path.read_text())


def _parse_tsv(tsv_text: str) -> dict:
    """Parse prost TSV output into structured hits."""
    hits = []
    reader = csv.DictReader(StringIO(tsv_text), delimiter="\t")
    for row in reader:
        hits.append({
            "target": row.get("target", row.get("subject", "")),
            "description": row.get("description", ""),
            "evalue": float(row.get("evalue", row.get("E-value", 999))),
            "score": float(row.get("score", row.get("bit_score", 0))),
            "identity": float(row.get("identity", row.get("pident", 0))),
        })

    return {
        "source": "prost",
        "hits": hits[:20],
        "total_hits": len(hits),
    }


def run_prost(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: run prost for each gene."""
    if not config.tools.prost_db_path:
        logger.warning("PROST_DB_PATH not set, skipping prost")
        return 0

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "prost"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        result = run_prost_single(gene.protein_sequence, gene.locus_tag)
        if not result.get("hits"):
            continue

        result["source"] = "PROST"
        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("prost"),
            payload=result,
            source_ref="prost",
            confidence=0.8,
        )
        count += 1
        logger.info("prost %s: %d hits", gene.locus_tag, len(result["hits"]))

    return count
