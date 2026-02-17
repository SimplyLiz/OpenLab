"""Operon prediction — group consecutive same-strand genes by intergenic distance.

Pure algorithm: genes on the same strand within 150bp of each other are
grouped into operons. Known functions within each operon provide
context for unknown genes.
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

MAX_INTERGENIC_DISTANCE = 150  # bp


def predict_operons(genes: list[Gene]) -> list[list[Gene]]:
    """Group genes into predicted operons based on strand and distance."""
    sorted_genes = sorted(genes, key=lambda g: g.start)
    operons: list[list[Gene]] = []
    current_operon: list[Gene] = []

    for gene in sorted_genes:
        if not current_operon:
            current_operon = [gene]
            continue

        prev = current_operon[-1]
        intergenic = gene.start - prev.end
        same_strand = gene.strand == prev.strand

        if same_strand and 0 <= intergenic <= MAX_INTERGENIC_DISTANCE:
            current_operon.append(gene)
        else:
            if len(current_operon) >= 2:
                operons.append(current_operon)
            current_operon = [gene]

    if len(current_operon) >= 2:
        operons.append(current_operon)

    return operons


def _known_functions_in_operon(operon_genes: list[Gene], target_tag: str) -> list[dict]:
    """Get known functions from other genes in the same operon."""
    known = []
    for gene in operon_genes:
        if gene.locus_tag == target_tag:
            continue
        product = gene.product or ""
        if product and "hypothetical" not in product.lower() and "uncharacterized" not in product.lower():
            known.append({
                "locus_tag": gene.locus_tag,
                "name": gene.name or "",
                "product": product,
                "distance": abs(gene.start),
            })
    return known


def run_operon_prediction(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: predict operons and store evidence for unknown genes."""
    # Need all genes for operon context, not just unknown ones
    all_genes = db.query(Gene).filter(Gene.start > 0).order_by(Gene.start).all()
    if not all_genes:
        return 0

    operons = predict_operons(all_genes)
    logger.info("Predicted %d operons from %d genes", len(operons), len(all_genes))

    # Map locus_tag -> operon
    gene_to_operon: dict[str, list[Gene]] = {}
    for operon_id, operon_genes in enumerate(operons):
        for gene in operon_genes:
            gene_to_operon[gene.locus_tag] = operon_genes

    count = 0
    target_tags = {g.locus_tag for g in genes}

    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "operon_prediction"):
            continue
        if gene.locus_tag not in gene_to_operon:
            continue

        operon_genes = gene_to_operon[gene.locus_tag]
        known = _known_functions_in_operon(operon_genes, gene.locus_tag)
        confidence = 0.5 if known else 0.3

        evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=evidence_type_for("operon_prediction"),
            payload={
                "source": "operon_prediction",
                "operon_size": len(operon_genes),
                "operon_members": [g.locus_tag for g in operon_genes],
                "known_functions": known,
                "strand": gene.strand,
                "operon_start": operon_genes[0].start,
                "operon_end": operon_genes[-1].end,
            },
            source_ref="operon_prediction",
            confidence=confidence,
        )
        count += 1

    logger.info("Operon evidence stored for %d genes", count)
    return count
