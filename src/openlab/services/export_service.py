"""Export service — produce structured data for DNAView consumption."""

import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from openlab.db.models.gene import Gene
from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.db.models.hypothesis import Hypothesis


# Keyword-based function categorization
_CATEGORY_PATTERNS = {
    "enzyme": [
        r"kinase", r"transferase", r"hydrolase", r"synthase", r"synthetase",
        r"reductase", r"oxidase", r"dehydrogenase", r"ligase", r"isomerase",
        r"mutase", r"lyase", r"protease", r"peptidase", r"esterase",
        r"phosphatase", r"nuclease", r"helicase", r"topoisomerase",
        r"polymerase", r"primase", r"enolase", r"catalytic", r"catalyzes",
        r"phosphodiesterase", r"thioredoxin", r"deaminase", r"glycosyl",
    ],
    "transporter": [
        r"transporter", r"permease", r"pump", r"channel", r"efflux",
        r"influx", r"import", r"export", r"ABC\s+transport", r"antiporter",
        r"symporter", r"porin", r"uptake",
    ],
    "regulatory": [
        r"regulat", r"repressor", r"activator", r"transcription factor",
        r"sigma factor", r"anti-sigma", r"response regulator",
        r"two-component", r"sensor", r"signal", r"modulator",
    ],
    "structural": [
        r"structural", r"scaffold", r"cytoskeleton", r"filament",
        r"ftsZ", r"mreB", r"actin-like", r"tubulin-like",
    ],
    "cell_division": [
        r"cell division", r"septation", r"fts[A-Z]", r"division",
        r"cytokinesis", r"divisome", r"min[CDE]",
    ],
    "dna_repair": [
        r"DNA repair", r"recombination", r"rec[A-Z]", r"uvr[A-Z]",
        r"mismatch", r"excision", r"endonuclease", r"DNA damage",
        r"SOS response",
    ],
    "translation": [
        r"ribosom", r"tRNA", r"aminoacyl", r"translation",
        r"elongation factor", r"initiation factor", r"release factor",
        r"peptidyl", r"30S", r"50S", r"rRNA",
    ],
    "transcription": [
        r"RNA polymerase", r"transcription", r"sigma", r"rpoA",
        r"rpoB", r"rpoC", r"rpoD", r"rpoE", r"nusA", r"nusB",
    ],
    "membrane_biogenesis": [
        r"membrane", r"lipid", r"fatty acid", r"lipoprotein",
        r"phospholipid", r"glycolipid", r"acyl", r"lipase",
        r"membrane protein", r"integral membrane",
    ],
}


def classify_function(proposed_function: str) -> str:
    """Categorize a proposed function into a functional category."""
    if not proposed_function:
        return "unknown_essential"

    text = proposed_function.lower()
    best_cat = "unknown_essential"
    best_score = 0

    for category, patterns in _CATEGORY_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score > best_score:
            best_score = score
            best_cat = category

    return best_cat


def _extract_evidence_summary(evidence_rows: list[Evidence]) -> dict:
    """Build a compact evidence summary."""
    counts: dict[str, int] = {}
    go_terms: set[str] = set()
    ec_numbers: set[str] = set()

    for ev in evidence_rows:
        ev_type = ev.evidence_type.value
        counts[ev_type] = counts.get(ev_type, 0) + 1

        p = ev.payload or {}

        for go in p.get("go_terms", []):
            if isinstance(go, dict):
                go_id = go.get("id", "")
                if go_id:
                    go_terms.add(go_id)
            elif isinstance(go, str) and go.startswith("GO:"):
                go_terms.add(go.split(":")[0] + ":" + go.split(":")[1]
                             if ":" in go else go)

        if p.get("ec_number"):
            ec_numbers.add(p["ec_number"])
        for hit in p.get("hits", []):
            ec = hit.get("ec_number", "")
            if ec:
                ec_numbers.add(ec)

    return {
        "countsByType": counts,
        "totalCount": len(evidence_rows),
        "goTerms": sorted(go_terms),
        "ecNumbers": sorted(ec_numbers),
    }


def export_graduated_genes(db: Session) -> dict:
    """Export all graduated genes with their hypotheses and evidence summaries."""
    genes = (
        db.query(Gene)
        .filter(Gene.graduated_at.isnot(None))
        .options(
            joinedload(Gene.evidence),
            joinedload(Gene.graduation_hypothesis),
        )
        .order_by(Gene.start)
        .all()
    )

    entries = []
    for gene in genes:
        hyp = gene.graduation_hypothesis
        confidence = hyp.confidence_score if hyp else None
        convergence = hyp.convergence_score if hyp else None

        category = classify_function(gene.proposed_function or "")
        evidence_summary = _extract_evidence_summary(gene.evidence)

        entry = {
            "locusTag": gene.locus_tag,
            "geneName": gene.name,
            "start": gene.start,
            "end": gene.end,
            "strand": gene.strand,
            "product": gene.product,
            "predictedFunction": gene.proposed_function,
            "confidenceScore": round(confidence, 3) if confidence is not None else None,
            "convergenceScore": round(convergence, 3) if convergence is not None else None,
            "functionCategory": category,
            "evidenceSummary": evidence_summary,
            "graduatedAt": gene.graduated_at.isoformat() if gene.graduated_at else None,
            "hypothesisId": hyp.hypothesis_id if hyp else None,
            "provenance": {
                "trustLevel": "predicted",
                "source": "BioLab",
                "retrievedAt": datetime.now(UTC).isoformat(),
            },
        }
        entries.append(entry)

    return {
        "version": "1.0",
        "organism": "JCVI-syn3A",
        "accession": "CP016816.2",
        "exportedAt": datetime.now(UTC).isoformat(),
        "totalGraduated": len(entries),
        "genes": entries,
    }
