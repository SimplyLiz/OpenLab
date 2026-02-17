"""HHpred remote homology search via MPI Bioinformatics Toolkit.

Submits protein sequence to HHpred, polls for completion (up to 60 min),
parses hit table.
"""

from __future__ import annotations

import logging
import re
import time

import httpx
from sqlalchemy.orm import Session

from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

TOOLKIT_API = "https://toolkit.tuebingen.mpg.de/api/jobs"


async def search_hhpred(http: httpx.AsyncClient, protein_seq: str) -> dict:
    """Submit sequence to HHpred and return remote homology hits."""
    if not protein_seq or len(protein_seq) < 20:
        return {"source": "hhpred"}

    try:
        # Submit job
        resp = await http.post(
            TOOLKIT_API,
            json={
                "tool": "hhpred",
                "parameters": {
                    "sequence": protein_seq,
                    "hhpred_db": "pdb70",
                },
            },
            timeout=30.0,
        )
        if resp.status_code not in (200, 201, 202):
            return {"source": "hhpred"}

        data = resp.json()
        job_id = data.get("id") or data.get("jobId", "")
        if not job_id:
            return {"source": "hhpred"}

        # Poll for completion (up to 60 min)
        import asyncio
        for _ in range(360):
            await asyncio.sleep(10)
            status_resp = await http.get(f"{TOOLKIT_API}/{job_id}", timeout=10.0)
            if status_resp.status_code != 200:
                continue
            status = status_resp.json().get("status", "")
            if status == "DONE":
                result_resp = await http.get(
                    f"{TOOLKIT_API}/{job_id}/results", timeout=30.0
                )
                if result_resp.status_code == 200:
                    return _parse_hhpred_results(result_resp.json())
                break
            if status in ("ERROR", "FAILED"):
                break

    except Exception as e:
        logger.debug("HHpred search failed: %s", e)

    return {"source": "hhpred"}


def _parse_hhpred_results(data: dict) -> dict:
    """Parse HHpred result JSON into evidence payload."""
    hits = []
    for hit in data.get("hits", data.get("results", []))[:20]:
        prob = hit.get("prob", hit.get("probability", 0))
        evalue = hit.get("evalue", hit.get("e-value", 999))
        description = hit.get("description", hit.get("desc", ""))

        if isinstance(prob, str):
            try:
                prob = float(prob)
            except ValueError:
                prob = 0

        hits.append({
            "target": hit.get("target", hit.get("id", "")),
            "description": description,
            "probability": prob,
            "evalue": evalue,
            "score": hit.get("score", 0),
            "aligned_cols": hit.get("aligned_cols", 0),
        })

    return {
        "source": "hhpred",
        "hits": hits,
        "total_hits": len(hits),
    }


def _confidence_from_probability(prob: float) -> float:
    """Map HHpred probability to confidence score."""
    if prob >= 95:
        return 0.9
    if prob >= 80:
        return 0.7
    if prob >= 50:
        return 0.5
    return 0.3


def run_hhpred(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: submit genes to HHpred."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "hhpred"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        try:
            # Submit
            resp = http.post(
                TOOLKIT_API,
                json={
                    "tool": "hhpred",
                    "parameters": {
                        "sequence": gene.protein_sequence,
                        "hhpred_db": "pdb70",
                    },
                },
                timeout=30.0,
            )
            if resp.status_code not in (200, 201, 202):
                continue

            data = resp.json()
            job_id = data.get("id") or data.get("jobId", "")
            if not job_id:
                continue

            # Poll (up to 60 min)
            result_data = None
            for _ in range(360):
                time.sleep(10)
                status_resp = http.get(f"{TOOLKIT_API}/{job_id}", timeout=10.0)
                if status_resp.status_code != 200:
                    continue
                status = status_resp.json().get("status", "")
                if status == "DONE":
                    result_resp = http.get(f"{TOOLKIT_API}/{job_id}/results", timeout=30.0)
                    if result_resp.status_code == 200:
                        result_data = _parse_hhpred_results(result_resp.json())
                    break
                if status in ("ERROR", "FAILED"):
                    break

            if not result_data or not result_data.get("hits"):
                continue

            top_prob = max(h.get("probability", 0) for h in result_data["hits"])
            confidence = _confidence_from_probability(top_prob)

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("hhpred"),
                payload={
                    "source": "HHpred",
                    "hits": result_data["hits"],
                    "total_hits": result_data["total_hits"],
                },
                source_ref="hhpred",
                confidence=confidence,
            )
            count += 1
            logger.info("HHpred %s: %d hits, top prob=%.1f",
                        gene.locus_tag, len(result_data["hits"]), top_prob)

        except Exception as e:
            logger.warning("HHpred %s error: %s", gene.locus_tag, e)

    return count
