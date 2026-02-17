"""eggNOG-mapper local — run emapper.py locally against downloaded database.

Parses the .emapper.annotations TSV for COG, GO, EC, KEGG, and PFAM annotations.
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


def run_eggnog_single(protein_seq: str, locus_tag: str) -> dict:
    """Run eggnog-mapper locally on a single sequence."""
    db_path = config.tools.eggnog_db_path
    if not db_path or not Path(db_path).exists():
        return {"source": "eggnog"}

    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = Path(tmpdir) / "input.fasta"
        fasta_path.write_text(f">{locus_tag}\n{protein_seq}\n")
        prefix = Path(tmpdir) / "output"

        try:
            subprocess.run(
                [
                    "emapper.py",
                    "-i", str(fasta_path),
                    "-o", str(prefix),
                    "--data_dir", db_path,
                    "-m", "diamond",
                    "--no_annot", "false",
                    "--cpu", "4",
                ],
                capture_output=True, text=True, timeout=600,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug("emapper failed for %s: %s", locus_tag, e)
            return {"source": "eggnog"}

        annotations_file = Path(f"{prefix}.emapper.annotations")
        if not annotations_file.exists():
            return {"source": "eggnog"}

        return _parse_annotations(annotations_file.read_text())


def _parse_annotations(text: str) -> dict:
    """Parse .emapper.annotations TSV file."""
    result: dict = {"source": "eggnog"}

    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue

        fields = line.split("\t")
        if len(fields) < 13:
            continue

        # Standard eggnog-mapper v2 columns
        # 0=query, 1=seed_ortholog, 2=evalue, 3=score, 4=eggNOG_OGs,
        # 5=max_annot_lvl, 6=COG_category, 7=Description, 8=Preferred_name,
        # 9=GOs, 10=EC, 11=KEGG_ko, 12=KEGG_Pathway, 13=KEGG_Module,
        # 14=KEGG_Reaction, 15=KEGG_rclass, 16=BRITE, 17=KEGG_TC,
        # 18=CAZy, 19=BiGG_Reaction, 20=PFAMs

        def _field(idx: int) -> str:
            return fields[idx].strip() if idx < len(fields) and fields[idx] != "-" else ""

        seed = _field(1)
        if seed:
            result["seed_ortholog"] = seed
        evalue = _field(2)
        if evalue:
            try:
                result["evalue"] = float(evalue)
            except ValueError:
                pass

        cog = _field(6)
        if cog:
            result["cog_category"] = cog

        description = _field(7)
        if description:
            result["description"] = description

        name = _field(8)
        if name:
            result["preferred_name"] = name

        go_raw = _field(9)
        if go_raw:
            go_terms = [g.strip() for g in go_raw.split(",") if g.strip().startswith("GO:")]
            if go_terms:
                result["go_terms"] = go_terms

        ec_raw = _field(10)
        if ec_raw:
            ec_numbers = [e.strip() for e in ec_raw.split(",") if e.strip()]
            if ec_numbers:
                result["ec_numbers"] = ec_numbers

        kegg_ko = _field(11)
        if kegg_ko:
            result["kegg_ko"] = kegg_ko

        kegg_pathway = _field(12)
        if kegg_pathway:
            result["kegg_pathway"] = kegg_pathway

        pfam_raw = _field(20) if len(fields) > 20 else ""
        if pfam_raw:
            result["pfam_domains"] = [p.strip() for p in pfam_raw.split(",") if p.strip()]

        break  # Only first data line

    return result


def run_eggnog_local(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: run local eggnog-mapper for each gene."""
    db_path = config.tools.eggnog_db_path
    if not db_path or not Path(db_path).exists():
        logger.warning("EGGNOG_DB_PATH not set or not found, skipping local eggnog")
        return 0

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "eggnog"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        result = run_eggnog_single(gene.protein_sequence, gene.locus_tag)
        if len(result) <= 1:  # just "source"
            continue

        result["source"] = "eggNOG"
        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("eggnog"),
            payload=result,
            source_ref="eggnog",
            confidence=0.7,
        )
        count += 1
        logger.info("eggnog_local %s: %s", gene.locus_tag,
                    result.get("description", "no description"))

    return count
