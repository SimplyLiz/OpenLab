"""Validation service — leave-one-out, convergence, FPR measurement."""

import logging
import random
import re
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.db.models.gene import Gene
from openlab.db.models.hypothesis import Hypothesis
from openlab.services import gene_service, llm_service
from openlab.services.convergence import compute_convergence_from_orm
from openlab.services.evidence_normalizer import normalize_evidence, _map_keywords_to_go

logger = logging.getLogger(__name__)


def leave_one_out(
    db: Session,
    gene_ids: list[int] | None = None,
) -> list[dict]:
    """Leave-one-out validation on genes with curated reclassification evidence.

    For each qualifying gene:
    1. Load all evidence
    2. Remove curated_reclassification evidence
    3. Build synthesis prompt from remaining evidence
    4. Call LLM to predict function
    5. Compare to curated function
    """
    curated_evidence = (
        db.query(Evidence)
        .filter(
            Evidence.evidence_type == EvidenceType.LITERATURE,
            Evidence.source_ref.like("CuratedReclassification:%"),
        )
        .all()
    )

    curated_by_gene: dict[int, Evidence] = {}
    for ev in curated_evidence:
        curated_by_gene[ev.gene_id] = ev

    if gene_ids:
        curated_by_gene = {
            gid: ev for gid, ev in curated_by_gene.items() if gid in gene_ids
        }

    results = []

    for gene_id, curated_ev in curated_by_gene.items():
        gene = db.query(Gene).filter(Gene.gene_id == gene_id).first()
        if not gene:
            continue

        curated_function = (curated_ev.payload or {}).get("predicted_function", "")
        if not curated_function:
            continue

        evidence_rows = (
            db.query(Evidence)
            .filter(
                Evidence.gene_id == gene_id,
                ~Evidence.source_ref.like("CuratedReclassification:%"),
            )
            .order_by(Evidence.evidence_type, Evidence.evidence_id)
            .all()
        )

        if not evidence_rows:
            results.append({
                "gene_id": gene_id,
                "locus_tag": gene.locus_tag,
                "curated_function": curated_function,
                "predicted_function": "",
                "match_score": 0.0,
                "confidence": 0.0,
                "passed": False,
                "reason": "no evidence without curated data",
            })
            continue

        # Build a simple prompt from evidence payloads
        prompt_lines = [
            f"Gene: {gene.locus_tag}",
            f"Current annotation: {gene.product or 'hypothetical protein'}",
            "",
            "Evidence:",
        ]
        for ev in evidence_rows:
            source = (ev.payload or {}).get("source", ev.evidence_type.value)
            prompt_lines.append(f"- {source}: {ev.payload}")
        prompt = "\n".join(prompt_lines)

        try:
            response = llm_service.synthesize(
                prompt, purpose="validation", gene_locus_tag=gene.locus_tag,
            )
        except Exception as exc:
            logger.warning(f"LOO validation: LLM error for {gene.locus_tag}: {exc}")
            results.append({
                "gene_id": gene_id,
                "locus_tag": gene.locus_tag,
                "curated_function": curated_function,
                "predicted_function": "",
                "match_score": 0.0,
                "confidence": 0.0,
                "passed": False,
                "reason": f"LLM error: {exc}",
            })
            continue

        confidence = _extract_confidence(response)
        predicted = _extract_predicted_function(response)
        match_score = _compare_functions(curated_function, predicted)

        results.append({
            "gene_id": gene_id,
            "locus_tag": gene.locus_tag,
            "curated_function": curated_function,
            "predicted_function": predicted,
            "match_score": round(match_score, 3),
            "confidence": confidence,
            "passed": match_score >= 0.3,
            "reason": "",
        })

    return results


def _extract_confidence(response: str) -> float:
    """Extract confidence score from LLM response."""
    patterns = [
        r"[Cc]onfidence[:\s*]+(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*/\s*1\.0",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            try:
                score = float(match.group(1))
                if score > 1.0:
                    score = score / 100.0
                return round(max(0.0, min(1.0, score)), 2)
            except ValueError:
                continue
    return 0.3


def _extract_predicted_function(response: str) -> str:
    """Extract the predicted function from an LLM response."""
    patterns = [
        r"[Pp]redicted\s+function[:\s]+(.+?)(?:\n|$)",
        r"[Mm]ost\s+likely\s+function[:\s]+(.+?)(?:\n|$)",
        r"1\.\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            return match.group(1).strip()

    lines = response.strip().split("\n")
    if lines:
        return lines[0][:200]
    return ""


def _compare_functions(curated: str, predicted: str) -> float:
    """Compare curated vs predicted function using keyword overlap."""
    stopwords = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "and", "or", "but", "in",
        "on", "at", "to", "for", "of", "with", "by", "from", "as", "into",
        "through", "during", "before", "after", "above", "below", "this",
        "that", "these", "those", "it", "its", "protein", "gene", "function",
        "likely", "possibly", "probably", "predicted",
    }

    def tokenize(text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return {w for w in words if w not in stopwords and len(w) > 2}

    curated_terms = tokenize(curated)
    predicted_terms = tokenize(predicted)

    if not curated_terms or not predicted_terms:
        return 0.0

    intersection = curated_terms & predicted_terms
    union = curated_terms | predicted_terms

    return len(intersection) / len(union) if union else 0.0


def compute_all_convergence(db: Session) -> list[dict]:
    """Batch compute convergence scores for all genes with hypotheses."""
    hypotheses = (
        db.query(Hypothesis)
        .filter(Hypothesis.gene_id.isnot(None))
        .all()
    )

    results = []
    for hyp in hypotheses:
        gene = db.query(Gene).filter(Gene.gene_id == hyp.gene_id).first()
        if not gene:
            continue

        conv_score = gene_service.compute_convergence_score(db, hyp.gene_id)

        hyp.convergence_score = conv_score
        db.flush()

        results.append({
            "gene_id": hyp.gene_id,
            "locus_tag": gene.locus_tag,
            "convergence_score": conv_score,
            "confidence_score": hyp.confidence_score,
            "hypothesis_id": hyp.hypothesis_id,
        })

    db.commit()
    return results


# ── Ortholog cross-validation ──────────────────────────────────────


def _load_orthologs(ortholog_path: str | Path | None = None) -> dict:
    """Load ortholog mapping from YAML file."""
    if ortholog_path is None:
        ortholog_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "mgen_orthologs.yaml"
    else:
        ortholog_path = Path(ortholog_path)

    if not ortholog_path.exists():
        logger.warning(f"Ortholog file not found: {ortholog_path}")
        return {}

    return yaml.safe_load(ortholog_path.read_text()) or {}


def ortholog_validation(
    db: Session,
    ortholog_path: str | Path | None = None,
) -> list[dict]:
    """Validate graduated gene predictions against known M. genitalium orthologs."""
    orthologs = _load_orthologs(ortholog_path)
    if not orthologs:
        return []

    graduated = gene_service.list_graduated_genes(db, limit=9999)

    results = []
    for gene in graduated:
        if gene.locus_tag not in orthologs:
            continue

        ortholog = orthologs[gene.locus_tag]
        ortholog_function = ortholog.get("ortholog_function", "")
        proposed = gene.proposed_function or ""

        if not proposed or not ortholog_function:
            continue

        _, proposed_cats = _map_keywords_to_go(proposed)
        _, ortholog_cats = _map_keywords_to_go(ortholog_function)

        match_score = _compare_functions(ortholog_function, proposed)

        if proposed_cats and ortholog_cats:
            cat_overlap = len(proposed_cats & ortholog_cats) / len(proposed_cats | ortholog_cats)
        elif not proposed_cats and not ortholog_cats:
            cat_overlap = 0.5
        else:
            cat_overlap = 0.0

        combined = 0.6 * match_score + 0.4 * cat_overlap
        passed = combined >= 0.2

        results.append({
            "gene_id": gene.gene_id,
            "locus_tag": gene.locus_tag,
            "proposed_function": proposed,
            "ortholog_gene": ortholog.get("ortholog_gene", ""),
            "ortholog_function": ortholog_function,
            "match_score": round(match_score, 3),
            "category_overlap": round(cat_overlap, 3),
            "combined_score": round(combined, 3),
            "passed": passed,
            "proposed_categories": sorted(proposed_cats),
            "ortholog_categories": sorted(ortholog_cats),
        })

    return results


# ── Consistency validation ─────────────────────────────────────────


def consistency_validation(db: Session) -> list[dict]:
    """Check if each graduated gene's proposed_function matches its evidence majority."""
    graduated = gene_service.list_graduated_genes(db, limit=9999)

    results = []
    for gene in graduated:
        proposed = gene.proposed_function or ""
        if not proposed:
            continue

        evidence_rows = (
            db.query(Evidence).filter(Evidence.gene_id == gene.gene_id).all()
        )
        if not evidence_rows:
            continue

        cat_counts: dict[str, int] = {}
        for ev in evidence_rows:
            norm = normalize_evidence(ev)
            for cat in norm.categories:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

        if not cat_counts:
            continue

        total = sum(cat_counts.values())
        majority_cats = {
            cat for cat, cnt in cat_counts.items()
            if cnt >= 2 or cnt / total >= 0.3
        }
        if not majority_cats:
            majority_cats = {max(cat_counts, key=cat_counts.get)}

        _, proposed_cats = _map_keywords_to_go(proposed)

        consistent = bool(proposed_cats & majority_cats) if proposed_cats else True

        results.append({
            "gene_id": gene.gene_id,
            "locus_tag": gene.locus_tag,
            "proposed_function": proposed,
            "proposed_categories": sorted(proposed_cats),
            "evidence_majority_categories": sorted(majority_cats),
            "evidence_category_counts": cat_counts,
            "consistent": consistent,
        })

    return results


# ── Bootstrap stability ────────────────────────────────────────────


def bootstrap_stability(
    db: Session,
    gene_id: int,
    n_iterations: int = 50,
    sample_fraction: float = 0.7,
) -> dict:
    """Assess convergence score stability via bootstrap resampling."""
    evidence_rows = (
        db.query(Evidence).filter(Evidence.gene_id == gene_id).all()
    )

    if len(evidence_rows) < 3:
        base_score = compute_convergence_from_orm(evidence_rows)
        return {
            "gene_id": gene_id,
            "base_score": base_score,
            "mean": base_score,
            "std": 0.0,
            "ci_lower": base_score,
            "ci_upper": base_score,
            "n_iterations": 0,
            "n_evidence": len(evidence_rows),
            "stable": True,
        }

    base_score = compute_convergence_from_orm(evidence_rows)

    sample_size = max(2, int(len(evidence_rows) * sample_fraction))
    scores: list[float] = []

    for _ in range(n_iterations):
        sample = random.sample(evidence_rows, sample_size)
        score = compute_convergence_from_orm(sample)
        scores.append(score)

    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std = variance ** 0.5

    scores_sorted = sorted(scores)
    ci_lower = scores_sorted[int(0.025 * len(scores_sorted))]
    ci_upper = scores_sorted[int(0.975 * len(scores_sorted))]

    return {
        "gene_id": gene_id,
        "base_score": base_score,
        "mean": round(mean_score, 3),
        "std": round(std, 3),
        "ci_lower": round(ci_lower, 3),
        "ci_upper": round(ci_upper, 3),
        "n_iterations": n_iterations,
        "n_evidence": len(evidence_rows),
        "stable": std < 0.15,
    }


# ── Combined validation ───────────────────────────────────────────


def validate_all(
    db: Session,
    ortholog_path: str | Path | None = None,
    run_bootstrap: bool = False,
    bootstrap_limit: int = 20,
) -> dict:
    """Run all validation methods and produce a combined report."""
    orth_results = ortholog_validation(db, ortholog_path)
    orth_passed = sum(1 for r in orth_results if r["passed"])
    orth_accuracy = orth_passed / len(orth_results) if orth_results else 0.0

    cons_results = consistency_validation(db)
    cons_consistent = sum(1 for r in cons_results if r["consistent"])
    cons_rate = cons_consistent / len(cons_results) if cons_results else 0.0

    report: dict = {
        "ortholog": {
            "results": orth_results,
            "accuracy": round(orth_accuracy, 3),
            "n_tested": len(orth_results),
            "n_passed": orth_passed,
        },
        "consistency": {
            "results": cons_results,
            "rate": round(cons_rate, 3),
            "n_tested": len(cons_results),
            "n_consistent": cons_consistent,
        },
    }

    if run_bootstrap:
        graduated = gene_service.list_graduated_genes(db, limit=bootstrap_limit)
        boot_results = []
        for gene in graduated:
            boot = bootstrap_stability(db, gene.gene_id)
            boot["locus_tag"] = gene.locus_tag
            boot_results.append(boot)

        stable_count = sum(1 for b in boot_results if b["stable"])
        report["bootstrap"] = {
            "results": boot_results,
            "stability_rate": round(stable_count / len(boot_results), 3) if boot_results else 0.0,
            "n_tested": len(boot_results),
            "n_stable": stable_count,
        }

    estimated_fpr = 1.0 - (orth_accuracy * 0.5 + cons_rate * 0.5) if orth_results else 1.0 - cons_rate
    report["summary"] = {
        "ortholog_accuracy": round(orth_accuracy, 3),
        "consistency_rate": round(cons_rate, 3),
        "estimated_fpr": round(max(0, estimated_fpr), 3),
    }

    return report


# ── Confidence tiers ─────────────────────────────────────────────


def build_confidence_tiers(
    db: Session,
    ortholog_path: str | Path | None = None,
) -> dict:
    """Categorize graduated genes into confidence tiers based on convergence + validation."""
    orth_results = ortholog_validation(db, ortholog_path)
    cons_results = consistency_validation(db)

    orth_by_tag: dict[str, dict] = {r["locus_tag"]: r for r in orth_results}
    cons_by_tag: dict[str, dict] = {r["locus_tag"]: r for r in cons_results}

    graduated = gene_service.list_graduated_genes(db, limit=9999)

    tiers: dict[int, list[dict]] = {1: [], 2: [], 3: [], 4: []}

    for gene in graduated:
        tag = gene.locus_tag
        proposed = gene.proposed_function or ""

        hyp = (
            db.query(Hypothesis)
            .filter(Hypothesis.gene_id == gene.gene_id)
            .order_by(Hypothesis.hypothesis_id.desc())
            .first()
        )
        conv_score = hyp.convergence_score if hyp and hyp.convergence_score else 0.0
        conf_score = hyp.confidence_score if hyp and hyp.confidence_score else 0.0

        ev_count = db.query(Evidence).filter(Evidence.gene_id == gene.gene_id).count()

        orth = orth_by_tag.get(tag)
        cons = cons_by_tag.get(tag)

        orth_passed = orth["passed"] if orth else None
        cons_passed = cons["consistent"] if cons else True

        tier = _classify_tier(conv_score, orth_passed, cons_passed)

        entry = {
            "gene_id": gene.gene_id,
            "locus_tag": tag,
            "proposed_function": proposed,
            "convergence_score": conv_score,
            "confidence_score": conf_score,
            "evidence_count": ev_count,
            "ortholog_passed": orth_passed,
            "consistency_passed": cons_passed,
            "tier": tier,
        }
        tiers[tier].append(entry)

    all_genes = []
    for tier_genes in tiers.values():
        all_genes.extend(tier_genes)

    tier_summary = {}
    for tier_num, tier_genes in tiers.items():
        if tier_genes:
            mean_conv = sum(g["convergence_score"] for g in tier_genes) / len(tier_genes)
        else:
            mean_conv = 0.0
        tier_summary[str(tier_num)] = {
            "count": len(tier_genes),
            "mean_convergence": round(mean_conv, 3),
        }

    return {
        "tiers": {str(k): v for k, v in tiers.items()},
        "summary": {
            "total_graduated": len(all_genes),
            "tier_breakdown": tier_summary,
        },
    }


def _classify_tier(conv_score: float, orth_passed: bool | None, cons_passed: bool) -> int:
    """Classify a gene into a confidence tier (1-4)."""
    if orth_passed is False:
        return 4
    if not cons_passed and conv_score < 0.1:
        return 4
    if conv_score >= 0.5 and cons_passed and orth_passed is not False:
        return 1
    if 0.2 <= conv_score < 0.5 and (cons_passed or orth_passed is True):
        return 2
    if conv_score >= 0.5 and not cons_passed:
        return 2
    return 3
