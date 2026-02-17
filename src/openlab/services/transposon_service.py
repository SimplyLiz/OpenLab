"""Transposon mutagenesis import service."""

from pathlib import Path

from sqlalchemy.orm import Session

from openlab.ingestion.transposon import TransposonEntry, parse_transposon_tsv
from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.db.models.gene import Gene

# Confidence mapping from Tn5 class
CLASS_CONFIDENCE = {
    "e": 0.95,  # essential — zero insertions tolerated
    "i": 0.85,  # quasi-essential — growth impaired
    "n": 0.90,  # non-essential — gene clearly dispensable
    "d": 0.70,  # disrupted — ambiguous, could be artifact
}


def import_transposon_data(
    db: Session,
    path: Path | str,
) -> dict:
    """Parse transposon TSV and create TRANSPOSON evidence + update Gene.essentiality."""
    entries = parse_transposon_tsv(path)
    imported = 0
    skipped = 0
    updated = 0

    for entry in entries:
        gene = db.query(Gene).filter(Gene.locus_tag == entry.locus_tag).first()
        if gene is None:
            skipped += 1
            continue

        existing = (
            db.query(Evidence)
            .filter(
                Evidence.gene_id == gene.gene_id,
                Evidence.evidence_type == EvidenceType.TRANSPOSON,
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        payload = {
            "source": "Hutchison2016",
            "doi": "10.1126/science.aad6253",
            "tn5_class": entry.tn5_class,
            "essentiality": entry.essentiality,
            "n_insertions": entry.n_insertions,
        }
        if entry.notes:
            payload["notes"] = entry.notes

        ev = Evidence(
            gene_id=gene.gene_id,
            evidence_type=EvidenceType.TRANSPOSON,
            payload=payload,
            source_ref="Hutchison2016 DOI:10.1126/science.aad6253",
            confidence=CLASS_CONFIDENCE.get(entry.tn5_class, 0.5),
        )
        db.add(ev)

        if not gene.essentiality:
            gene.essentiality = entry.essentiality
            updated += 1

        imported += 1

    db.commit()

    return {
        "file": str(path),
        "total_entries": len(entries),
        "imported": imported,
        "skipped": skipped,
        "genes_updated": updated,
    }
