"""ESMFold structure prediction via HuggingFace Inference API.

Submits protein sequence to facebook/esmfold_v1, saves PDB output,
extracts pLDDT from B-factor column.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from openlab.config import config
from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.services import evidence_service
from openlab.registry import evidence_type_for

logger = logging.getLogger(__name__)

ESMFOLD_URL = "https://router.huggingface.co/hf-inference/models/facebook/esmfold_v1"


async def search_esmfold(http: httpx.AsyncClient, protein_seq: str) -> dict:
    """Submit sequence to ESMFold and return PDB + pLDDT."""
    token = config.tools.hf_token
    if not token:
        return {"source": "esmfold"}
    if not protein_seq or len(protein_seq) < 10:
        return {"source": "esmfold"}

    try:
        resp = await http.post(
            ESMFOLD_URL,
            content=protein_seq,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/plain",
            },
            timeout=120.0,
        )
        if resp.status_code != 200:
            logger.debug("ESMFold HTTP %d: %s", resp.status_code, resp.text[:200])
            return {"source": "esmfold"}

        pdb_text = resp.text
        plddt = _parse_mean_plddt(pdb_text)

        return {
            "source": "esmfold",
            "pdb_text": pdb_text,
            "mean_plddt": round(plddt, 1),
            "residue_count": len(protein_seq),
        }
    except Exception as e:
        logger.debug("ESMFold failed: %s", e)
        return {"source": "esmfold"}


def _parse_mean_plddt(pdb_text: str) -> float:
    """Extract mean pLDDT from B-factor column of ATOM records."""
    values = []
    for line in pdb_text.splitlines():
        if line.startswith("ATOM") and len(line) >= 66:
            try:
                bfactor = float(line[60:66].strip())
                values.append(bfactor)
            except ValueError:
                continue
    return sum(values) / len(values) if values else 0.0


def _save_pdb(locus_tag: str, pdb_text: str) -> Path:
    """Save PDB file to structure directory."""
    struct_dir = Path(config.tools.structure_dir)
    struct_dir.mkdir(parents=True, exist_ok=True)
    path = struct_dir / f"{locus_tag}_esmfold.pdb"
    path.write_text(pdb_text)
    return path


def run_esmfold(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: predict structure for each gene via ESMFold."""
    token = config.tools.hf_token
    if not token:
        logger.warning("HF_TOKEN not set, skipping ESMFold")
        return 0

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "esmfold"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 10:
            continue

        try:
            resp = http.post(
                ESMFOLD_URL,
                content=gene.protein_sequence,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "text/plain",
                },
                timeout=120.0,
            )
            if resp.status_code != 200:
                logger.debug("ESMFold %s HTTP %d", gene.locus_tag, resp.status_code)
                continue

            pdb_text = resp.text
            plddt = _parse_mean_plddt(pdb_text)
            pdb_path = _save_pdb(gene.locus_tag, pdb_text)
            confidence = 0.6 if plddt > 70 else 0.3

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("esmfold"),
                payload={
                    "source": "ESMFold",
                    "mean_plddt": round(plddt, 1),
                    "pdb_path": str(pdb_path),
                    "residue_count": len(gene.protein_sequence),
                },
                source_ref="esmfold",
                confidence=confidence,
            )
            count += 1
            logger.info("ESMFold %s: pLDDT=%.1f", gene.locus_tag, plddt)

        except Exception as e:
            logger.warning("ESMFold %s error: %s", gene.locus_tag, e)

    return count
