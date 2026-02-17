"""Phylogenetic profiling — co-occurrence analysis across reference proteomes.

Uses DIAMOND BLAST to build a presence/absence matrix of protein homologs
across reference proteomes, then computes Jaccard similarity to find
co-evolving gene pairs.
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


def _build_presence_matrix(
    genes: list[Gene],
    proteomes_dir: str,
    evalue_cutoff: float = 1e-5,
) -> dict[str, dict[str, bool]]:
    """Build presence/absence matrix: gene -> {proteome -> present}."""
    proteomes_path = Path(proteomes_dir)
    if not proteomes_path.exists():
        return {}

    proteome_files = list(proteomes_path.glob("*.fasta")) + list(proteomes_path.glob("*.fa"))
    if not proteome_files:
        return {}

    matrix: dict[str, dict[str, bool]] = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write all query sequences
        query_path = Path(tmpdir) / "queries.fasta"
        with open(query_path, "w") as f:
            for gene in genes:
                if gene.protein_sequence:
                    f.write(f">{gene.locus_tag}\n{gene.protein_sequence}\n")

        for proteome_file in proteome_files:
            proteome_name = proteome_file.stem
            db_path = Path(tmpdir) / f"{proteome_name}.dmnd"

            try:
                # Build DIAMOND database
                subprocess.run(
                    ["diamond", "makedb", "--in", str(proteome_file), "--db", str(db_path)],
                    capture_output=True, timeout=120,
                )

                # Run DIAMOND BLAST
                out_path = Path(tmpdir) / f"{proteome_name}.tsv"
                subprocess.run(
                    [
                        "diamond", "blastp",
                        "-q", str(query_path),
                        "-d", str(db_path),
                        "-o", str(out_path),
                        "--outfmt", "6", "qseqid", "sseqid", "evalue",
                        "-e", str(evalue_cutoff),
                        "--max-target-seqs", "1",
                    ],
                    capture_output=True, timeout=300,
                )

                if out_path.exists():
                    for line in out_path.read_text().splitlines():
                        fields = line.split("\t")
                        if len(fields) >= 3:
                            qseqid = fields[0]
                            if qseqid not in matrix:
                                matrix[qseqid] = {}
                            matrix[qseqid][proteome_name] = True

            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.debug("DIAMOND failed for %s: %s", proteome_name, e)

    return matrix


def _compute_jaccard_similarity(
    matrix: dict[str, dict[str, bool]],
    gene_tag: str,
    all_proteomes: set[str],
) -> list[dict]:
    """Find genes with similar phylogenetic profiles."""
    if gene_tag not in matrix:
        return []

    target_profile = set(matrix[gene_tag].keys())
    if not target_profile:
        return []

    similar = []
    for other_tag, other_hits in matrix.items():
        if other_tag == gene_tag:
            continue
        other_profile = set(other_hits.keys())
        union = target_profile | other_profile
        if not union:
            continue
        jaccard = len(target_profile & other_profile) / len(union)
        if jaccard >= 0.3:
            similar.append({
                "locus_tag": other_tag,
                "jaccard": round(jaccard, 3),
                "shared_proteomes": len(target_profile & other_profile),
                "total_proteomes": len(union),
            })

    similar.sort(key=lambda x: -x["jaccard"])
    return similar[:10]


def run_phylogenetic_profile(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: build phylogenetic profiles and find co-occurring genes."""
    proteomes_dir = config.tools.proteomes_dir
    if not proteomes_dir or not Path(proteomes_dir).exists():
        logger.warning("PROTEOMES_DIR not set or not found, skipping phylogenetic profiles")
        return 0

    # Build matrix once for all genes
    matrix = _build_presence_matrix(genes, proteomes_dir)
    if not matrix:
        logger.info("No phylogenetic profile data generated")
        return 0

    all_proteomes = set()
    for hits in matrix.values():
        all_proteomes.update(hits.keys())

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "phylogenetic_profile"):
            continue
        if gene.locus_tag not in matrix:
            continue

        similar = _compute_jaccard_similarity(matrix, gene.locus_tag, all_proteomes)
        profile = matrix.get(gene.locus_tag, {})

        if not similar and not profile:
            continue

        top_jaccard = similar[0]["jaccard"] if similar else 0
        confidence = 0.6 if top_jaccard >= 0.5 else 0.4

        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("phylogenetic_profile"),
            payload={
                "source": "PhylogeneticProfile",
                "similar_genes": similar,
                "proteomes_present": len(profile),
                "proteomes_total": len(all_proteomes),
                "presence_fraction": round(len(profile) / len(all_proteomes), 3) if all_proteomes else 0,
            },
            source_ref="phylogenetic_profile",
            confidence=confidence,
        )
        count += 1

    logger.info("Phylogenetic profiles: %d genes profiled across %d proteomes",
                count, len(all_proteomes))
    return count
