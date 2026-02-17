"""hmmscan — HMMER domain search against Pfam database.

Runs hmmscan subprocess, parses tblout for domain hits with E-values,
creates ProteinFeature rows for each domain.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from openlab.config import config
from openlab.db.models.gene import Gene, ProteinFeature
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)


def run_hmmscan_single(protein_seq: str, locus_tag: str) -> dict:
    """Run hmmscan on a single sequence and return parsed results."""
    pfam_db = config.tools.pfam_db_path
    if not pfam_db or not Path(pfam_db).exists():
        return {"source": "hmmscan"}

    with tempfile.TemporaryDirectory() as tmpdir:
        query_path = Path(tmpdir) / "query.fasta"
        query_path.write_text(f">{locus_tag}\n{protein_seq}\n")
        tblout_path = Path(tmpdir) / "results.tblout"

        try:
            subprocess.run(
                [
                    "hmmscan", "--tblout", str(tblout_path),
                    "--noali", "-E", "1e-5",
                    pfam_db, str(query_path),
                ],
                capture_output=True, text=True, timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("hmmscan failed for %s: %s", locus_tag, e)
            return {"source": "hmmscan"}

        if not tblout_path.exists():
            return {"source": "hmmscan"}

        return _parse_tblout(tblout_path.read_text())


def _parse_tblout(tblout_text: str) -> dict:
    """Parse hmmscan --tblout output into structured hits."""
    hits = []
    for line in tblout_text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        fields = line.split()
        if len(fields) < 18:
            continue

        hits.append({
            "target_name": fields[0],
            "accession": fields[1],
            "query_name": fields[2],
            "evalue": float(fields[4]),
            "score": float(fields[5]),
            "bias": float(fields[6]),
            "dom_evalue": float(fields[7]),
            "dom_score": float(fields[8]),
            "description": " ".join(fields[18:]),
        })

    return {
        "source": "hmmscan",
        "hits": hits,
        "total_hits": len(hits),
    }


def run_hmmscan(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: run hmmscan for each gene."""
    pfam_db = config.tools.pfam_db_path
    if not pfam_db or not Path(pfam_db).exists():
        logger.warning("PFAM_DB_PATH not set or not found, skipping hmmscan")
        return 0

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "hmmscan"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        result = run_hmmscan_single(gene.protein_sequence, gene.locus_tag)
        if not result.get("hits"):
            continue

        # Create ProteinFeature rows for domain hits
        for hit in result["hits"]:
            feature = ProteinFeature(
                gene_id=gene.gene_id,
                feature_type=f"domain:{hit['target_name']}",
                start=0,
                end=gene.length or 0,
                score=hit["evalue"],
                source="hmmscan",
                source_version=hit["accession"],
            )
            db.add(feature)

        result["source"] = "hmmscan"
        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("hmmscan"),
            payload=result,
            source_ref="hmmscan",
            confidence=0.7,
        )
        count += 1
        logger.info("hmmscan %s: %d domain hits", gene.locus_tag, len(result["hits"]))

    return count
