"""Pipeline persistence — maps pipeline COMPLETED events to DB operations.

Pipeline stays pure (no DB imports). This module bridges the gap
by taking event data dicts and routing them to the appropriate
service/ORM calls.
"""

import logging

from sqlalchemy.orm import Session

from openlab.db.models.evidence import EvidenceType
from openlab.db.models.gene import Gene
from openlab.services import evidence_service, gene_service, hypothesis_service

logger = logging.getLogger(__name__)

# Core pipeline evidence source → EvidenceType mapping.
# Contrib sources (dnasyn, etc.) are registered via the plugin registry.
_CORE_SOURCE_TO_EVIDENCE_TYPE: dict[str, EvidenceType] = {
    "protein_features": EvidenceType.COMPUTATIONAL,
    "cdd": EvidenceType.STRUCTURE,
    "ncbi_blast": EvidenceType.HOMOLOGY,
    "interpro": EvidenceType.COMPUTATIONAL,
    "string": EvidenceType.COMPUTATIONAL,
    "uniprot": EvidenceType.LITERATURE,
    "literature": EvidenceType.LITERATURE,
}


def get_source_evidence_type(source: str) -> EvidenceType:
    """Look up evidence type for a source, checking core then registry."""
    ev_type = _CORE_SOURCE_TO_EVIDENCE_TYPE.get(source)
    if ev_type is not None:
        return ev_type
    # Fall through to plugin registry
    from openlab.registry import get_evidence_type_map
    return get_evidence_type_map().get(source, EvidenceType.COMPUTATIONAL)


# Backwards-compatible alias used by _persist_single_prediction
SOURCE_TO_EVIDENCE_TYPE = _CORE_SOURCE_TO_EVIDENCE_TYPE


def persist_event(db: Session, stage: str, data: dict) -> None:
    """Dispatch a pipeline COMPLETED event to the right persistence function."""
    handlers = {
        "genome_ingest": persist_genome_genes,
        "functional_prediction": persist_functional_analysis,
        "gene_analysis": persist_gene_analysis,
        "essentiality_prediction": persist_essentiality,
    }
    handler = handlers.get(stage)
    if handler:
        handler(db, data)


def persist_genome_genes(db: Session, genome_data: dict) -> None:
    """Upsert Gene rows from genome_ingest COMPLETED data."""
    genes = genome_data.get("genes", [])
    if not genes:
        return

    count = 0
    for g in genes:
        locus_tag = g.get("locus_tag")
        if not locus_tag:
            continue

        existing = db.query(Gene).filter(Gene.locus_tag == locus_tag).first()
        if existing:
            # Update mutable fields
            existing.product = g.get("product") or existing.product
            existing.protein_sequence = g.get("protein_sequence") or existing.protein_sequence
            existing.length = g.get("protein_length", g.get("length", existing.length))
            existing.strand = g.get("strand", existing.strand)
            existing.start = g.get("start", existing.start)
            existing.end = g.get("end", existing.end)
        else:
            gene = Gene(
                locus_tag=locus_tag,
                name=g.get("gene_name") or g.get("name"),
                sequence=g.get("dna_sequence", ""),
                protein_sequence=g.get("protein_sequence"),
                length=g.get("protein_length", g.get("length", 0)),
                strand=g.get("strand", 1),
                start=g.get("start", 0),
                end=g.get("end", 0),
                product=g.get("product"),
            )
            db.add(gene)
        count += 1

    db.commit()
    logger.info("Persisted %d genes from genome_ingest", count)


def persist_functional_analysis(db: Session, analysis_data: dict) -> None:
    """Persist predictions from functional_prediction COMPLETED data (batch)."""
    predictions = analysis_data.get("predictions", [])
    for pred in predictions:
        _persist_single_prediction(db, pred)


def persist_gene_analysis(db: Session, prediction_data: dict) -> None:
    """Persist a single gene_analysis COMPLETED result."""
    _persist_single_prediction(db, prediction_data)


def _persist_single_prediction(db: Session, pred: dict) -> None:
    """Persist evidence + hypothesis for a single gene prediction."""
    locus_tag = pred.get("locus_tag")
    if not locus_tag:
        return

    gene = db.query(Gene).filter(Gene.locus_tag == locus_tag).first()
    if not gene:
        logger.warning("Gene %s not found in DB, skipping prediction persistence", locus_tag)
        return

    evidence_entries = pred.get("evidence", [])
    evidence_ids: list[int] = []

    for ev_data in evidence_entries:
        source = ev_data.get("source", "")
        ev_type = get_source_evidence_type(source)

        ev = evidence_service.add_evidence(
            db,
            gene_id=gene.gene_id,
            evidence_type=ev_type,
            payload=ev_data.get("payload", {}),
            source_ref=source,
            confidence=ev_data.get("confidence"),
        )
        evidence_ids.append(ev.evidence_id)

    # Create hypothesis if present
    hyp_data = pred.get("hypothesis")
    if hyp_data and evidence_ids:
        predicted_fn = hyp_data.get("predicted_function", "")
        confidence = hyp_data.get("confidence_score", 0.0)
        raw_response = hyp_data.get("raw_response", "")

        hypothesis_service.create_hypothesis(
            db,
            title=predicted_fn[:300] if predicted_fn else f"Hypothesis for {locus_tag}",
            description=raw_response,
            confidence_score=confidence,
            evidence_ids=evidence_ids,
            gene_id=gene.gene_id,
        )

    # Update convergence score
    if evidence_ids:
        gene_service.compute_convergence_score(db, gene.gene_id)

    logger.info(
        "Persisted %d evidence + hypothesis for %s",
        len(evidence_ids), locus_tag,
    )


def persist_essentiality(db: Session, essentiality_data: dict) -> None:
    """Update Gene.essentiality from essentiality_prediction COMPLETED data."""
    predictions = essentiality_data.get("predictions", {})
    if not predictions:
        return

    count = 0
    for locus_tag, is_essential in predictions.items():
        gene = db.query(Gene).filter(Gene.locus_tag == locus_tag).first()
        if gene:
            gene.essentiality = "essential" if is_essential else "non-essential"
            count += 1

    db.commit()
    logger.info("Updated essentiality for %d genes", count)
