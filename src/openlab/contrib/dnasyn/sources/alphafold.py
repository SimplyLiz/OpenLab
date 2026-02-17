"""AlphaFold DB structure retrieval.

Fetches pre-computed structures from AlphaFold EBI API using UniProt accessions
found in existing HOMOLOGY evidence.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from openlab.config import config
from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

ALPHAFOLD_API = "https://alphafold.ebi.ac.uk/api/prediction"


async def search_alphafold(http: httpx.AsyncClient, accession: str) -> dict:
    """Fetch AlphaFold prediction for a UniProt accession."""
    if not accession:
        return {"source": "alphafold"}

    try:
        resp = await http.get(f"{ALPHAFOLD_API}/{accession}", timeout=30.0)
        if resp.status_code != 200:
            return {"source": "alphafold"}

        data = resp.json()
        if not data:
            return {"source": "alphafold"}

        entry = data[0] if isinstance(data, list) else data
        pdb_url = entry.get("pdbUrl", "")
        confidence = entry.get("globalMetricValue", 0) or 0

        result = {
            "source": "alphafold",
            "accession": accession,
            "pdb_url": pdb_url,
            "global_plddt": round(confidence, 1),
            "model_version": entry.get("latestVersion", ""),
        }

        if pdb_url:
            pdb_resp = await http.get(pdb_url, timeout=30.0)
            if pdb_resp.status_code == 200:
                result["pdb_text"] = pdb_resp.text

        return result
    except Exception as e:
        logger.debug("AlphaFold lookup failed for %s: %s", accession, e)
        return {"source": "alphafold"}


def _extract_uniprot_accession(db: Session, gene_id: int) -> str | None:
    """Find a UniProt accession from existing evidence for this gene."""
    evidence_rows = (
        db.query(Evidence)
        .filter(
            Evidence.gene_id == gene_id,
            Evidence.evidence_type.in_([EvidenceType.HOMOLOGY, EvidenceType.LITERATURE]),
        )
        .all()
    )
    for ev in evidence_rows:
        payload = ev.payload or {}
        acc = payload.get("accession", "")
        if acc and len(acc) >= 6 and "_" not in acc:
            return acc
        # Check nested hits
        for hit in payload.get("hits", []):
            acc = hit.get("accession", "")
            if acc and len(acc) >= 6 and "_" not in acc:
                return acc
    return None


def _save_pdb(locus_tag: str, pdb_text: str) -> Path:
    struct_dir = Path(config.tools.structure_dir)
    struct_dir.mkdir(parents=True, exist_ok=True)
    path = struct_dir / f"{locus_tag}_alphafold.pdb"
    path.write_text(pdb_text)
    return path


def run_alphafold(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: fetch AlphaFold structures for genes with UniProt accessions."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "alphafold"):
            continue

        accession = _extract_uniprot_accession(db, gene.gene_id)
        if not accession:
            continue

        try:
            resp = http.get(f"{ALPHAFOLD_API}/{accession}", timeout=30.0)
            if resp.status_code != 200:
                continue

            data = resp.json()
            entry = data[0] if isinstance(data, list) else data
            pdb_url = entry.get("pdbUrl", "")
            global_plddt = entry.get("globalMetricValue", 0) or 0

            pdb_path = None
            if pdb_url:
                pdb_resp = http.get(pdb_url, timeout=30.0)
                if pdb_resp.status_code == 200:
                    pdb_path = _save_pdb(gene.locus_tag, pdb_resp.text)

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("alphafold"),
                payload={
                    "source": "AlphaFold",
                    "accession": accession,
                    "global_plddt": round(global_plddt, 1),
                    "pdb_path": str(pdb_path) if pdb_path else "",
                    "model_version": entry.get("latestVersion", ""),
                },
                source_ref="alphafold",
                confidence=0.7,
            )
            count += 1
            logger.info("AlphaFold %s: accession=%s pLDDT=%.1f", gene.locus_tag, accession, global_plddt)

        except Exception as e:
            logger.warning("AlphaFold %s error: %s", gene.locus_tag, e)

    return count
