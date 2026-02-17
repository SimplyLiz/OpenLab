"""Foldseek local — structure similarity search using local foldseek binary.

Runs foldseek easy-search against a local PDB100 database,
enriches hit descriptions via RCSB PDB API.
"""

from __future__ import annotations

import logging
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


def run_foldseek_single(pdb_path: str, db_path: str) -> dict:
    """Run local foldseek easy-search on a PDB file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "results.tsv"
        tmp_path = Path(tmpdir) / "tmp"
        tmp_path.mkdir()

        try:
            subprocess.run(
                [
                    "foldseek", "easy-search",
                    pdb_path, db_path, str(out_path), str(tmp_path),
                    "--format-output", "query,target,fident,alnlen,evalue,bits,tmscore,taxname",
                ],
                capture_output=True, text=True, timeout=300,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("foldseek local failed: %s", e)
            return {"source": "foldseek_local"}

        if not out_path.exists():
            return {"source": "foldseek_local"}

        return _parse_results(out_path.read_text())


def _parse_results(tsv_text: str) -> dict:
    """Parse foldseek TSV output."""
    hits = []
    for line in tsv_text.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 6:
            continue

        try:
            tmscore = float(fields[6]) if len(fields) > 6 else 0
        except (ValueError, IndexError):
            tmscore = 0

        if tmscore < 0.3:
            continue

        hits.append({
            "target": fields[1],
            "fident": float(fields[2]) if fields[2] else 0,
            "alnlen": int(fields[3]) if fields[3] else 0,
            "evalue": float(fields[4]) if fields[4] else 999,
            "bits": float(fields[5]) if fields[5] else 0,
            "tmscore": tmscore,
            "taxname": fields[7] if len(fields) > 7 else "",
        })

    hits.sort(key=lambda h: -h["tmscore"])
    return {
        "source": "foldseek_local",
        "hits": hits[:15],
        "total_hits": len(hits),
    }


def _enrich_descriptions(hits: list[dict], http: httpx.Client) -> list[dict]:
    """Enrich hit descriptions via RCSB PDB API."""
    for hit in hits:
        pdb_id = hit["target"].split("_")[0][:4] if hit.get("target") else ""
        if not pdb_id or len(pdb_id) != 4:
            continue

        try:
            resp = http.get(
                f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}",
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                hit["description"] = (
                    data.get("struct", {}).get("title", "") or
                    data.get("struct", {}).get("pdbx_descriptor", "")
                )
        except Exception:
            pass

    return hits


def run_foldseek_local(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: local foldseek search for genes with structures."""
    struct_dir = Path(config.tools.structure_dir)
    # Look for a local foldseek database
    foldseek_db = struct_dir / "pdb100"
    if not foldseek_db.exists():
        foldseek_db = struct_dir / "pdb100_db"
    if not foldseek_db.exists():
        logger.warning("No local foldseek database found in %s", struct_dir)
        return 0

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "foldseek_local"):
            continue

        # Find PDB file
        pdb_path = None
        for suffix in ("_esmfold.pdb", "_alphafold.pdb"):
            candidate = struct_dir / f"{gene.locus_tag}{suffix}"
            if candidate.exists():
                pdb_path = str(candidate)
                break

        if not pdb_path:
            continue

        result = run_foldseek_single(pdb_path, str(foldseek_db))
        if not result.get("hits"):
            continue

        # Enrich with PDB descriptions
        result["hits"] = _enrich_descriptions(result["hits"], http)

        top_tmscore = max(h.get("tmscore", 0) for h in result["hits"])
        confidence = 0.8 if top_tmscore > 0.5 else 0.5

        result["source"] = "FoldseekLocal"
        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("foldseek_local"),
            payload=result,
            source_ref="foldseek_local",
            confidence=confidence,
        )
        count += 1
        logger.info("foldseek_local %s: %d hits, top TM-score=%.2f",
                    gene.locus_tag, len(result["hits"]), top_tmscore)

    return count
