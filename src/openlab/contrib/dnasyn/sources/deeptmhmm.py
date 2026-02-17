"""DeepTMHMM — transmembrane topology prediction.

Uses biolib CLI or pybiolib to run DTU/DeepTMHMM.
Parses topology string and creates ProteinFeature rows for TM helices
and signal peptides.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from openlab.db.models.gene import Gene, ProteinFeature
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)


def run_deeptmhmm_single(protein_seq: str, locus_tag: str) -> dict:
    """Run DeepTMHMM on a single sequence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = Path(tmpdir) / "input.fasta"
        fasta_path.write_text(f">{locus_tag}\n{protein_seq}\n")

        # Try biolib CLI first
        try:
            result = subprocess.run(
                ["biolib", "run", "DTU/DeepTMHMM", "--fasta", str(fasta_path)],
                capture_output=True, text=True, timeout=300,
                cwd=tmpdir,
            )
            return _parse_deeptmhmm_output(tmpdir, result.stdout)
        except FileNotFoundError:
            pass

        # Fallback: pybiolib
        try:
            import pybiolib
            app = pybiolib.load("DTU/DeepTMHMM")
            job = app.cli(args=["--fasta", str(fasta_path)])
            job.save_files(tmpdir)
            return _parse_deeptmhmm_output(tmpdir)
        except (ImportError, Exception) as e:
            logger.debug("DeepTMHMM failed for %s: %s", locus_tag, e)

    return {"source": "deeptmhmm"}


def _parse_deeptmhmm_output(output_dir: str, stdout: str = "") -> dict:
    """Parse DeepTMHMM output files or stdout."""
    result: dict = {"source": "deeptmhmm", "topology": "", "regions": []}

    # Look for prediction file
    output_path = Path(output_dir)
    for pred_file in output_path.rglob("predicted_topologies.3line"):
        text = pred_file.read_text()
        return _parse_topology_file(text)

    # Try parsing stdout
    if stdout:
        return _parse_topology_file(stdout)

    return result


def _parse_topology_file(text: str) -> dict:
    """Parse 3-line topology format: >header, sequence, topology string."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 3:
        return {"source": "deeptmhmm"}

    topology = lines[2] if not lines[2].startswith(">") else ""
    if not topology:
        for line in lines:
            if line and not line.startswith(">") and all(c in "MSIOB" for c in line.strip()):
                topology = line.strip()
                break

    if not topology:
        return {"source": "deeptmhmm"}

    regions = _extract_regions(topology)

    return {
        "source": "deeptmhmm",
        "topology": topology,
        "regions": regions,
        "has_tm_helix": any(r["type"] == "TM_helix" for r in regions),
        "has_signal_peptide": any(r["type"] == "signal_peptide" for r in regions),
        "tm_count": sum(1 for r in regions if r["type"] == "TM_helix"),
    }


def _extract_regions(topology: str) -> list[dict]:
    """Extract structured regions from topology string (M=TM, S=signal, O=outside, I=inside)."""
    regions = []
    char_map = {"M": "TM_helix", "S": "signal_peptide", "I": "inside", "O": "outside"}

    current_char = None
    start = 0

    for i, c in enumerate(topology):
        if c != current_char:
            if current_char and current_char in ("M", "S"):
                regions.append({
                    "type": char_map.get(current_char, current_char),
                    "start": start + 1,
                    "end": i,
                })
            current_char = c
            start = i

    # Last region
    if current_char and current_char in ("M", "S"):
        regions.append({
            "type": char_map.get(current_char, current_char),
            "start": start + 1,
            "end": len(topology),
        })

    return regions


def run_deeptmhmm(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: predict topology for each gene."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "deeptmhmm"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        result = run_deeptmhmm_single(gene.protein_sequence, gene.locus_tag)
        if not result.get("topology"):
            continue

        # Create ProteinFeature rows
        for region in result.get("regions", []):
            if region["type"] in ("TM_helix", "signal_peptide"):
                feature = ProteinFeature(
                    gene_id=gene.gene_id,
                    feature_type=region["type"],
                    start=region["start"],
                    end=region["end"],
                    score=None,
                    source="DeepTMHMM",
                )
                db.add(feature)

        result["source"] = "DeepTMHMM"
        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("deeptmhmm"),
            payload=result,
            source_ref="deeptmhmm",
            confidence=0.8,
        )
        count += 1
        logger.info("DeepTMHMM %s: %d TM helices, signal=%s",
                    gene.locus_tag, result.get("tm_count", 0),
                    result.get("has_signal_peptide", False))

    return count
