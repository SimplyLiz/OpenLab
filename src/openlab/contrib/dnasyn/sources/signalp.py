"""SignalP 6.0 — signal peptide prediction.

Uses biolib CLI to run DTU/SignalP-6, parses prediction results
for signal peptide type and cleavage site.
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


def run_signalp_single(protein_seq: str, locus_tag: str) -> dict:
    """Run SignalP 6.0 on a single sequence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fasta_path = Path(tmpdir) / "input.fasta"
        fasta_path.write_text(f">{locus_tag}\n{protein_seq}\n")

        try:
            result = subprocess.run(
                [
                    "biolib", "run", "DTU/SignalP-6",
                    "--fastafile", str(fasta_path),
                    "--organism", "other",
                ],
                capture_output=True, text=True, timeout=300,
                cwd=tmpdir,
            )
            return _parse_signalp_output(tmpdir, result.stdout)
        except FileNotFoundError:
            pass

        # Fallback: pybiolib
        try:
            import pybiolib
            app = pybiolib.load("DTU/SignalP-6")
            job = app.cli(args=["--fastafile", str(fasta_path), "--organism", "other"])
            job.save_files(tmpdir)
            return _parse_signalp_output(tmpdir)
        except (ImportError, Exception) as e:
            logger.debug("SignalP failed for %s: %s", locus_tag, e)

    return {"source": "signalp"}


def _parse_signalp_output(output_dir: str, stdout: str = "") -> dict:
    """Parse SignalP output files."""
    result: dict = {"source": "signalp"}

    # Look for prediction_results.txt
    output_path = Path(output_dir)
    for pred_file in output_path.rglob("prediction_results.txt"):
        text = pred_file.read_text()
        return _parse_prediction_results(text)

    # Also try output/ subdirectory
    for pred_file in output_path.rglob("*_summary.signalp5"):
        text = pred_file.read_text()
        return _parse_prediction_results(text)

    if stdout:
        return _parse_prediction_results(stdout)

    return result


def _parse_prediction_results(text: str) -> dict:
    """Parse SignalP prediction_results.txt format."""
    result: dict = {"source": "signalp"}

    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            fields = line.split()
        if len(fields) < 3:
            continue

        prediction = fields[1] if len(fields) > 1 else ""
        probability = 0.0
        if len(fields) > 2:
            try:
                probability = float(fields[2])
            except ValueError:
                pass

        # CS position (cleavage site)
        cs_pos = None
        if len(fields) > 3:
            cs_match = re.search(r"CS pos:\s*(\d+)-(\d+)", fields[-1] if len(fields) > 3 else "")
            if cs_match:
                cs_pos = {"start": int(cs_match.group(1)), "end": int(cs_match.group(2))}

        result.update({
            "prediction": prediction,
            "probability": probability,
            "has_signal_peptide": prediction.upper() not in ("OTHER", "NO", ""),
            "signal_type": prediction,
            "cleavage_site": cs_pos,
        })
        break

    return result


def run_signalp(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: predict signal peptides for each gene."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "signalp"):
            continue
        if not gene.protein_sequence or len(gene.protein_sequence) < 20:
            continue

        result = run_signalp_single(gene.protein_sequence, gene.locus_tag)
        if not result.get("prediction"):
            continue

        # Create ProteinFeature if signal peptide detected
        if result.get("has_signal_peptide") and result.get("cleavage_site"):
            cs = result["cleavage_site"]
            feature = ProteinFeature(
                gene_id=gene.gene_id,
                feature_type="signal_peptide",
                start=1,
                end=cs.get("end", cs.get("start", 30)),
                score=result.get("probability"),
                source="SignalP6",
            )
            db.add(feature)

        confidence = result.get("probability", 0.7)
        if confidence > 1.0:
            confidence = confidence / 100.0

        result["source"] = "SignalP6"
        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("signalp"),
            payload=result,
            source_ref="signalp",
            confidence=confidence,
        )
        count += 1
        logger.info("SignalP %s: %s (prob=%.2f)",
                    gene.locus_tag, result.get("prediction", "?"),
                    result.get("probability", 0))

    return count
