"""Genomic neighborhood — +/- 3 flanking genes by position.

Pure algorithm: identifies neighboring genes on the chromosome
and reports their known functions as context for unknown genes.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

NEIGHBOR_COUNT = 3  # genes on each side


def get_neighbors(all_genes: list[Gene], target_tag: str) -> dict:
    """Get +/- N neighbors for a gene by genomic position."""
    sorted_genes = sorted(all_genes, key=lambda g: g.start)
    tag_to_idx = {g.locus_tag: i for i, g in enumerate(sorted_genes)}

    idx = tag_to_idx.get(target_tag)
    if idx is None:
        return {"source": "genomic_neighborhood"}

    upstream = []
    downstream = []

    for i in range(max(0, idx - NEIGHBOR_COUNT), idx):
        g = sorted_genes[i]
        upstream.append({
            "locus_tag": g.locus_tag,
            "name": g.name or "",
            "product": g.product or "",
            "strand": g.strand,
            "start": g.start,
            "end": g.end,
            "distance": sorted_genes[idx].start - g.end,
        })

    for i in range(idx + 1, min(len(sorted_genes), idx + NEIGHBOR_COUNT + 1)):
        g = sorted_genes[i]
        downstream.append({
            "locus_tag": g.locus_tag,
            "name": g.name or "",
            "product": g.product or "",
            "strand": g.strand,
            "start": g.start,
            "end": g.end,
            "distance": g.start - sorted_genes[idx].end,
        })

    known_neighbors = [
        n for n in upstream + downstream
        if n["product"] and "hypothetical" not in n["product"].lower()
    ]

    return {
        "source": "GenomicNeighborhood",
        "upstream": upstream,
        "downstream": downstream,
        "total_neighbors": len(upstream) + len(downstream),
        "known_function_neighbors": len(known_neighbors),
    }


def run_genomic_neighborhood(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: compute genomic neighborhood for each gene."""
    all_genes = db.query(Gene).filter(Gene.start > 0).order_by(Gene.start).all()
    if not all_genes:
        return 0

    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "genomic_neighborhood"):
            continue

        result = get_neighbors(all_genes, gene.locus_tag)
        if result.get("total_neighbors", 0) == 0:
            continue

        confidence = 0.4 if result.get("known_function_neighbors", 0) > 0 else 0.2

        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("genomic_neighborhood"),
            payload=result,
            source_ref="genomic_neighborhood",
            confidence=confidence,
        )
        count += 1

    logger.info("Genomic neighborhood evidence stored for %d genes", count)
    return count
