"""Gene service -- shared logic for CLI and API."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, joinedload

from openlab.exceptions import GeneNotFoundError, HypothesisNotFoundError
from openlab.db.models.gene import Gene
from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.db.models.hypothesis import Hypothesis
from openlab.services.convergence import compute_convergence_from_orm


# ── Disagreement detection ──────────────────────────────────────────


@dataclass
class DisagreementPair:
    evidence_id_a: int
    evidence_id_b: int
    source_a: str
    source_b: str
    evidence_type_a: str
    evidence_type_b: str
    agreement_score: float
    categories_a: set[str] = field(default_factory=set)
    categories_b: set[str] = field(default_factory=set)
    keywords_a: set[str] = field(default_factory=set)
    keywords_b: set[str] = field(default_factory=set)


@dataclass
class DisagreementReport:
    gene_id: int
    convergence_score: float
    total_pairs: int
    disagreeing_pairs: list[DisagreementPair] = field(default_factory=list)


def _unknown_product_filter():
    """SQLAlchemy filter clause for genes with unknown function.

    Excludes graduated genes — they have a proposed_function and are no longer
    considered unknown, even though GenBank product is still "hypothetical protein".
    """
    return and_(
        Gene.graduated_at.is_(None),
        or_(
            Gene.product.is_(None),
            Gene.product.ilike("%hypothetical%"),
            Gene.product.ilike("%uncharacterized%"),
            Gene.product.ilike("%unknown function%"),
            Gene.product.ilike("%putative%"),
        ),
    )


def list_genes(
    db: Session,
    unknown_only: bool = False,
    limit: int = 500,
    offset: int = 0,
) -> list[Gene]:
    """List genes, optionally filtering to unknown-function only."""
    q = db.query(Gene)
    if unknown_only:
        q = q.filter(_unknown_product_filter())
    return q.order_by(Gene.start).offset(offset).limit(limit).all()


def get_gene(db: Session, gene_id: int) -> Gene:
    """Get a single gene by ID, with features and evidence loaded."""
    gene = (
        db.query(Gene)
        .options(joinedload(Gene.features), joinedload(Gene.evidence))
        .filter(Gene.gene_id == gene_id)
        .first()
    )
    if not gene:
        raise GeneNotFoundError(f"Gene {gene_id} not found")
    return gene


def get_gene_by_locus(db: Session, locus_tag: str) -> Gene:
    """Get a gene by locus tag."""
    gene = (
        db.query(Gene)
        .options(joinedload(Gene.features), joinedload(Gene.evidence))
        .filter(Gene.locus_tag == locus_tag)
        .first()
    )
    if not gene:
        raise GeneNotFoundError(f"Gene with locus_tag '{locus_tag}' not found")
    return gene


def search_genes(db: Session, query: str) -> list[Gene]:
    """Search genes by locus_tag, name, or product."""
    pattern = f"%{query}%"
    return (
        db.query(Gene)
        .filter(
            or_(
                Gene.locus_tag.ilike(pattern),
                Gene.name.ilike(pattern),
                Gene.product.ilike(pattern),
            )
        )
        .order_by(Gene.start)
        .all()
    )


def has_recent_evidence(
    db: Session,
    gene_id: int,
    evidence_type: EvidenceType,
    max_age_days: int = 30,
) -> bool:
    """Check if a gene already has evidence of a given type within max_age_days."""
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    return (
        db.query(Evidence)
        .filter(
            Evidence.gene_id == gene_id,
            Evidence.evidence_type == evidence_type,
            Evidence.created_at >= cutoff,
        )
        .first()
    ) is not None


def genes_without_evidence(db: Session) -> list[Gene]:
    """Find genes with unknown function that have zero evidence rows."""
    return (
        db.query(Gene)
        .outerjoin(Evidence)
        .filter(
            _unknown_product_filter(),
            Gene.protein_sequence.isnot(None),
        )
        .group_by(Gene.gene_id)
        .having(func.count(Evidence.evidence_id) == 0)
        .all()
    )


def genes_with_stale_evidence(db: Session, max_age_days: int = 30) -> list[Gene]:
    """Find genes where the newest evidence is older than max_age_days."""
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    recent_subq = (
        db.query(Evidence.gene_id)
        .filter(Evidence.created_at >= cutoff)
        .distinct()
        .subquery()
    )
    return (
        db.query(Gene)
        .join(Evidence)
        .filter(
            _unknown_product_filter(),
            Gene.protein_sequence.isnot(None),
            ~Gene.gene_id.in_(db.query(recent_subq.c.gene_id)),
        )
        .distinct()
        .all()
    )


def get_dossier(db: Session, gene_id: int) -> dict:
    """Build a full evidence dossier for a gene."""
    gene = get_gene(db, gene_id)
    evidence_by_type: dict[str, list] = {}
    for ev in gene.evidence:
        key = ev.evidence_type.value
        evidence_by_type.setdefault(key, []).append(
            {
                "evidence_id": ev.evidence_id,
                "payload": ev.payload,
                "source_ref": ev.source_ref,
                "confidence": ev.confidence,
                "quality_score": ev.quality_score,
            }
        )
    return {
        "gene_id": gene.gene_id,
        "locus_tag": gene.locus_tag,
        "name": gene.name,
        "product": gene.product,
        "essentiality": gene.essentiality,
        "proposed_function": gene.proposed_function,
        "graduated_at": gene.graduated_at,
        "graduation_hypothesis_id": gene.graduation_hypothesis_id,
        "evidence_count": len(gene.evidence),
        "evidence_by_type": evidence_by_type,
        "features": [
            {
                "feature_type": f.feature_type,
                "start": f.start,
                "end": f.end,
                "source": f.source,
            }
            for f in gene.features
        ],
    }


# ── Function extraction ───────────────────────────────────────────────


def extract_proposed_function(hypothesis: Hypothesis) -> str:
    """Extract the actual predicted function from a hypothesis description.

    Parses the LLM synthesis response stored in hypothesis.description,
    looking for patterns like "**Predicted function**: ..." or "Predicted function: ...".
    Strips locus tag prefix (e.g. "JCVISYN3A_0538 likely encodes" -> "likely encodes").
    Falls back to first line of description, truncated to 200 chars.
    """
    text = hypothesis.description or ""
    if not text.strip():
        return hypothesis.title

    patterns = [
        r"1\.\s*\*{0,2}[Pp]redicted\s+[Ff]unction\**[:\s*]+(.+?)(?:\n|$)",
        r"\*{0,2}[Pp]redicted\s+[Ff]unction\**[:\s*]+(.+?)(?:\n|$)",
        r"\*{0,2}[Mm]ost\s+likely\s+function\**[:\s*]+(.+?)(?:\n|$)",
        r"1\.\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            result = _clean_function_text(match.group(1))
            return result[:200] if result else hypothesis.title

    for line in text.strip().split("\n"):
        line = line.strip().lstrip("*").strip()
        if line:
            return _clean_function_text(line)[:200]

    return hypothesis.title


def _clean_function_text(text: str) -> str:
    """Strip markdown formatting and locus tag prefixes from extracted function text."""
    text = text.strip().strip("*").strip()
    text = re.sub(r"^JCVISYN3A_\d+\s+", "", text)
    text = re.sub(r"^[Tt]he\s+gene\s+JCVISYN3A_\d+\s+", "", text)
    text = re.sub(r"^[Tt]he\s+JCVISYN3A_\d+\s+gene\s+", "", text)
    if text:
        first_word = text.split()[0] if text.split() else ""
        if first_word == first_word.lower():
            text = text[0].upper() + text[1:]
    return text


# ── Graduation ────────────────────────────────────────────────────────


def graduate_gene(
    db: Session,
    gene_id: int,
    proposed_function: str,
    hypothesis_id: int | None = None,
) -> Gene:
    """Graduate a gene — assign a proposed function."""
    gene = get_gene(db, gene_id)

    if hypothesis_id is not None:
        hyp = db.query(Hypothesis).filter(
            Hypothesis.hypothesis_id == hypothesis_id
        ).first()
        if not hyp:
            raise HypothesisNotFoundError(
                f"Hypothesis {hypothesis_id} not found"
            )

    gene.proposed_function = proposed_function
    gene.graduated_at = datetime.now(UTC)
    gene.graduation_hypothesis_id = hypothesis_id
    db.commit()
    db.refresh(gene)
    return gene


def ungraduate_gene(db: Session, gene_id: int) -> Gene:
    """Reverse graduation — clear proposed_function and graduated_at."""
    gene = get_gene(db, gene_id)
    if gene.graduated_at is None:
        raise ValueError(
            f"Gene {gene_id} ({gene.locus_tag}) is not graduated"
        )
    gene.proposed_function = None
    gene.graduated_at = None
    gene.graduation_hypothesis_id = None
    db.commit()
    db.refresh(gene)
    return gene


def list_graduation_candidates(
    db: Session,
    min_confidence: float = 0.7,
    limit: int = 100,
) -> list[dict]:
    """Find genes eligible for graduation: unknown + not graduated + hypothesis above threshold."""
    rows = (
        db.query(Gene, Hypothesis)
        .join(Hypothesis, Hypothesis.gene_id == Gene.gene_id)
        .filter(
            _unknown_product_filter(),
            Hypothesis.confidence_score >= min_confidence,
        )
        .order_by(Hypothesis.confidence_score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "gene_id": gene.gene_id,
            "locus_tag": gene.locus_tag,
            "product": gene.product,
            "hypothesis_id": hyp.hypothesis_id,
            "hypothesis_title": hyp.title,
            "confidence": hyp.confidence_score,
            "proposed_function": extract_proposed_function(hyp),
        }
        for gene, hyp in rows
    ]


def list_graduated_genes(db: Session, limit: int = 500) -> list[Gene]:
    """Return all graduated genes, most recent first."""
    return (
        db.query(Gene)
        .filter(Gene.graduated_at.isnot(None))
        .order_by(Gene.graduated_at.desc())
        .limit(limit)
        .all()
    )


# ── Convergence scoring (DB entry point) ───────────────────────────


def compute_convergence_score(db: Session, gene_id: int) -> float:
    """Compute how much different evidence sources agree on a gene's function.

    Delegates to convergence.compute_convergence_from_orm().
    """
    evidence_rows = (
        db.query(Evidence)
        .filter(Evidence.gene_id == gene_id)
        .all()
    )
    return compute_convergence_from_orm(evidence_rows)


# ── Disagreement detection ──────────────────────────────────────────


def detect_disagreements(
    db: Session, gene_id: int, threshold: float = 0.2
) -> DisagreementReport:
    """Detect disagreements between evidence sources for a gene."""
    from openlab.services.evidence_normalizer import normalize_evidence
    from openlab.services.convergence import _pairwise_agreement

    evidence_rows = (
        db.query(Evidence).filter(Evidence.gene_id == gene_id).all()
    )

    convergence = compute_convergence_from_orm(evidence_rows)

    normalized = []
    for ev in evidence_rows:
        norm = normalize_evidence(ev)
        if norm.go_terms or norm.ec_numbers or norm.categories or norm.keywords:
            normalized.append((ev, norm))

    disagreeing: list[DisagreementPair] = []
    total_pairs = 0

    for i in range(len(normalized)):
        ev_i, norm_i = normalized[i]
        for j in range(i + 1, len(normalized)):
            ev_j, norm_j = normalized[j]
            total_pairs += 1

            sim = _pairwise_agreement(norm_i, norm_j)
            if sim < threshold:
                source_a = (ev_i.payload or {}).get("source", ev_i.evidence_type.value)
                source_b = (ev_j.payload or {}).get("source", ev_j.evidence_type.value)
                disagreeing.append(DisagreementPair(
                    evidence_id_a=ev_i.evidence_id,
                    evidence_id_b=ev_j.evidence_id,
                    source_a=source_a,
                    source_b=source_b,
                    evidence_type_a=ev_i.evidence_type.value,
                    evidence_type_b=ev_j.evidence_type.value,
                    agreement_score=round(sim, 3),
                    categories_a=norm_i.categories,
                    categories_b=norm_j.categories,
                    keywords_a=set(list(norm_i.keywords)[:10]),
                    keywords_b=set(list(norm_j.keywords)[:10]),
                ))

    return DisagreementReport(
        gene_id=gene_id,
        convergence_score=convergence,
        total_pairs=total_pairs,
        disagreeing_pairs=disagreeing,
    )


def detect_all_disagreements(
    db: Session, threshold: float = 0.2
) -> list[dict]:
    """Batch disagreement detection across all genes with evidence."""
    gene_ids = (
        db.query(Evidence.gene_id)
        .distinct()
        .all()
    )

    results = []
    for (gene_id,) in gene_ids:
        report = detect_disagreements(db, gene_id, threshold)
        if report.disagreeing_pairs:
            gene = db.query(Gene).filter(Gene.gene_id == gene_id).first()
            locus_tag = gene.locus_tag if gene else f"gene_{gene_id}"
            results.append({
                "gene_id": gene_id,
                "locus_tag": locus_tag,
                "convergence_score": report.convergence_score,
                "total_pairs": report.total_pairs,
                "disagreement_count": len(report.disagreeing_pairs),
                "top_disagreement": (
                    f"{report.disagreeing_pairs[0].source_a} vs "
                    f"{report.disagreeing_pairs[0].source_b}"
                    if report.disagreeing_pairs else ""
                ),
            })

    results.sort(key=lambda r: -r["disagreement_count"])
    return results
