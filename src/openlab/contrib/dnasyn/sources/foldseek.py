"""Foldseek online structure similarity search.

Submits PDB content to Foldseek web API, polls for results,
parses TSV hit table.
"""

from __future__ import annotations

import logging
import time

import httpx
from sqlalchemy.orm import Session

from openlab.config import config
from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

FOLDSEEK_API = "https://search.foldseek.com/api"


async def search_foldseek(http: httpx.AsyncClient, pdb_text: str) -> dict:
    """Submit PDB to Foldseek and return structural similarity hits."""
    if not pdb_text or len(pdb_text) < 100:
        return {"source": "foldseek"}

    try:
        # Submit search
        resp = await http.post(
            f"{FOLDSEEK_API}/ticket",
            data={
                "q": pdb_text,
                "mode": "3diaa",
                "database[]": ["afdb50", "pdb100"],
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            return {"source": "foldseek"}

        ticket = resp.json()
        ticket_id = ticket.get("id", "")
        if not ticket_id:
            return {"source": "foldseek"}

        # Poll for results (up to 5 min)
        for _ in range(60):
            await _async_sleep(5)
            status_resp = await http.get(f"{FOLDSEEK_API}/ticket/{ticket_id}", timeout=10.0)
            if status_resp.status_code != 200:
                continue
            status_data = status_resp.json()
            if status_data.get("status") == "COMPLETE":
                return _parse_foldseek_results(status_data)
            if status_data.get("status") in ("ERROR", "UNKNOWN"):
                break

    except Exception as e:
        logger.debug("Foldseek search failed: %s", e)

    return {"source": "foldseek"}


async def _async_sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)


def _parse_foldseek_results(data: dict) -> dict:
    """Parse Foldseek result payload into evidence dict."""
    hits = []
    for db_result in data.get("results", []):
        for alignment in db_result.get("alignments", [])[:15]:
            hit = {
                "target": alignment.get("target", ""),
                "description": alignment.get("tDescription", ""),
                "fident": alignment.get("fident", 0),
                "evalue": alignment.get("evalue", 999),
                "bits": alignment.get("bits", 0),
                "qstart": alignment.get("qstart", 0),
                "qend": alignment.get("qend", 0),
                "tstart": alignment.get("tstart", 0),
                "tend": alignment.get("tend", 0),
            }
            hits.append(hit)

    return {
        "source": "foldseek",
        "hits": hits[:15],
        "total_hits": len(hits),
    }


def _get_pdb_for_gene(gene: Gene) -> str | None:
    """Load PDB text from previously predicted structure files."""
    from pathlib import Path
    struct_dir = Path(config.tools.structure_dir)
    for suffix in ("_esmfold.pdb", "_alphafold.pdb"):
        pdb_path = struct_dir / f"{gene.locus_tag}{suffix}"
        if pdb_path.exists():
            return pdb_path.read_text()
    return None


def run_foldseek(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: search Foldseek for genes with predicted structures."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "foldseek"):
            continue

        pdb_text = _get_pdb_for_gene(gene)
        if not pdb_text:
            continue

        try:
            # Submit
            resp = http.post(
                f"{FOLDSEEK_API}/ticket",
                data={
                    "q": pdb_text,
                    "mode": "3diaa",
                    "database[]": ["afdb50", "pdb100"],
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                continue

            ticket_id = resp.json().get("id", "")
            if not ticket_id:
                continue

            # Poll
            result_data = None
            for _ in range(60):
                time.sleep(5)
                status_resp = http.get(f"{FOLDSEEK_API}/ticket/{ticket_id}", timeout=10.0)
                if status_resp.status_code != 200:
                    continue
                status_data = status_resp.json()
                if status_data.get("status") == "COMPLETE":
                    result_data = _parse_foldseek_results(status_data)
                    break
                if status_data.get("status") in ("ERROR", "UNKNOWN"):
                    break

            if not result_data or not result_data.get("hits"):
                continue

            top_fident = max(h.get("fident", 0) for h in result_data["hits"])
            confidence = 0.8 if top_fident > 0.3 else 0.4

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("foldseek"),
                payload={
                    "source": "Foldseek",
                    "hits": result_data["hits"],
                    "total_hits": result_data["total_hits"],
                },
                source_ref="foldseek",
                confidence=confidence,
            )
            count += 1
            logger.info("Foldseek %s: %d hits, top fident=%.2f",
                        gene.locus_tag, len(result_data["hits"]), top_fident)

        except Exception as e:
            logger.warning("Foldseek %s error: %s", gene.locus_tag, e)

    return count
