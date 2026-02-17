"""HHblits local homology search.

Runs hhblits subprocess against a local UniClust/BFD database,
parses the .hhr output file for homology hits.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from openlab.config import config
from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)


def run_hhblits_single(protein_seq: str, locus_tag: str) -> dict:
    """Run hhblits on a single sequence and return parsed results."""
    db_path = config.tools.hhblits_db_path
    if not db_path:
        return {"source": "hhblits"}

    with tempfile.TemporaryDirectory() as tmpdir:
        query_path = Path(tmpdir) / "query.fasta"
        query_path.write_text(f">{locus_tag}\n{protein_seq}\n")
        a3m_path = Path(tmpdir) / "result.a3m"
        hhr_path = Path(tmpdir) / "result.hhr"

        try:
            subprocess.run(
                [
                    "hhblits",
                    "-i", str(query_path),
                    "-d", db_path,
                    "-oa3m", str(a3m_path),
                    "-o", str(hhr_path),
                    "-n", "3",
                    "-cpu", "4",
                    "-v", "0",
                ],
                capture_output=True, text=True, timeout=600,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("hhblits failed for %s: %s", locus_tag, e)
            return {"source": "hhblits"}

        if not hhr_path.exists():
            return {"source": "hhblits"}

        return _parse_hhr(hhr_path.read_text())


def _parse_hhr(hhr_text: str) -> dict:
    """Parse .hhr result file into structured hits."""
    hits = []
    in_hitlist = False

    for line in hhr_text.splitlines():
        if line.startswith(" No Hit"):
            in_hitlist = True
            continue
        if in_hitlist and line.strip() == "":
            break
        if not in_hitlist:
            continue

        # Parse hit line: " 1 PDB_ID description   Prob  E-value  Score  ..."
        match = re.match(
            r"\s*\d+\s+(\S+)\s+(.+?)\s+(\d+\.?\d*)\s+(\S+)\s+(\S+)\s+(\S+)\s+",
            line,
        )
        if match:
            prob = float(match.group(3))
            try:
                evalue = float(match.group(4))
            except ValueError:
                evalue = 999.0

            hits.append({
                "target": match.group(1),
                "description": match.group(2).strip(),
                "probability": prob,
                "evalue": evalue,
                "score": float(match.group(5)) if match.group(5) != "NA" else 0,
            })

    return {
        "source": "hhblits",
        "hits": hits[:20],
        "total_hits": len(hits),
    }


def run_hhblits(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: run hhblits for each gene."""
    if not config.tools.hhblits_db_path:
        logger.warning("HHBLITS_DB_PATH not set, skipping hhblits")
        return 0

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "hhblits"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        result = run_hhblits_single(gene.protein_sequence, gene.locus_tag)
        if not result.get("hits"):
            continue

        top_prob = max(h.get("probability", 0) for h in result["hits"])
        confidence = 0.9 if top_prob > 90 else 0.6

        result["source"] = "HHblits"
        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("hhblits"),
            payload=result,
            source_ref="hhblits",
            confidence=confidence,
        )
        count += 1
        logger.info("hhblits %s: %d hits, top prob=%.1f",
                    gene.locus_tag, len(result["hits"]), top_prob)

    return count
