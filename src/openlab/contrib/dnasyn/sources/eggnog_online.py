"""eggNOG-mapper online API — functional annotation via orthology.

Submits protein sequence to eggNOG-mapper EMBL web service,
parses COG, GO, EC, KEGG from response.
"""

from __future__ import annotations

import logging
import time

import httpx
from sqlalchemy.orm import Session

from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

EGGNOG_API = "http://eggnog-mapper.embl.de/api/v2"


async def search_eggnog_online(http: httpx.AsyncClient, protein_seq: str) -> dict:
    """Submit sequence to eggNOG-mapper online and parse annotations."""
    if not protein_seq or len(protein_seq) < 20:
        return {"source": "eggnog"}

    try:
        # Submit job
        resp = await http.post(
            f"{EGGNOG_API}/job",
            json={"sequence": protein_seq},
            timeout=30.0,
        )
        if resp.status_code not in (200, 201, 202):
            return {"source": "eggnog"}

        job_data = resp.json()
        job_id = job_data.get("job_id") or job_data.get("id", "")
        if not job_id:
            return {"source": "eggnog"}

        # Poll for results (up to 10 min)
        import asyncio
        for _ in range(120):
            await asyncio.sleep(5)
            status_resp = await http.get(f"{EGGNOG_API}/job/{job_id}", timeout=10.0)
            if status_resp.status_code != 200:
                continue
            status_data = status_resp.json()
            if status_data.get("status") in ("done", "DONE", "finished"):
                return _parse_eggnog_result(status_data)
            if status_data.get("status") in ("error", "ERROR", "failed"):
                break

    except Exception as e:
        logger.debug("eggNOG online search failed: %s", e)

    return {"source": "eggnog"}


def _parse_eggnog_result(data: dict) -> dict:
    """Parse eggNOG-mapper result into evidence payload."""
    result: dict = {"source": "eggnog"}

    annotations = data.get("annotations", data.get("result", {}))
    if isinstance(annotations, list) and annotations:
        annotations = annotations[0]
    if not isinstance(annotations, dict):
        return result

    if annotations.get("COG_category"):
        result["cog_category"] = annotations["COG_category"]
    if annotations.get("Description"):
        result["description"] = annotations["Description"]
    if annotations.get("Preferred_name"):
        result["preferred_name"] = annotations["Preferred_name"]

    # GO terms
    go_raw = annotations.get("GOs", "")
    if go_raw and go_raw != "-":
        go_terms = [g.strip() for g in go_raw.split(",") if g.strip().startswith("GO:")]
        if go_terms:
            result["go_terms"] = go_terms

    # EC numbers
    ec_raw = annotations.get("EC", "")
    if ec_raw and ec_raw != "-":
        ec_numbers = [e.strip() for e in ec_raw.split(",") if e.strip()]
        if ec_numbers:
            result["ec_numbers"] = ec_numbers

    # KEGG
    kegg_raw = annotations.get("KEGG_ko", "") or annotations.get("KEGG_Pathway", "")
    if kegg_raw and kegg_raw != "-":
        result["kegg"] = kegg_raw

    # PFAM
    pfam_raw = annotations.get("PFAMs", "")
    if pfam_raw and pfam_raw != "-":
        result["pfam_domains"] = [p.strip() for p in pfam_raw.split(",") if p.strip()]

    return result


def run_eggnog_online(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: submit genes to eggNOG-mapper online API."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "eggnog"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        try:
            # Submit
            resp = http.post(
                f"{EGGNOG_API}/job",
                json={"sequence": gene.protein_sequence},
                timeout=30.0,
            )
            if resp.status_code not in (200, 201, 202):
                continue

            job_data = resp.json()
            job_id = job_data.get("job_id") or job_data.get("id", "")
            if not job_id:
                continue

            # Poll
            result_data = None
            for _ in range(120):
                time.sleep(5)
                status_resp = http.get(f"{EGGNOG_API}/job/{job_id}", timeout=10.0)
                if status_resp.status_code != 200:
                    continue
                status_data = status_resp.json()
                if status_data.get("status") in ("done", "DONE", "finished"):
                    result_data = _parse_eggnog_result(status_data)
                    break
                if status_data.get("status") in ("error", "ERROR", "failed"):
                    break

            if not result_data or len(result_data) <= 1:
                continue

            result_data["source"] = "eggNOG"
            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("eggnog"),
                payload=result_data,
                source_ref="eggnog",
                confidence=0.7,
            )
            count += 1
            logger.info("eggNOG %s: %s", gene.locus_tag,
                        result_data.get("description", "no description"))

        except Exception as e:
            logger.warning("eggNOG %s error: %s", gene.locus_tag, e)

    return count
