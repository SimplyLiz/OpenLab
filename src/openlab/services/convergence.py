"""Convergence scoring — measure how much independent evidence sources agree.

Ported from DNASyn's gene_service.py convergence scoring, adapted for
GeneLife's in-memory pipeline (no DB dependency).

Core idea: when BLAST, InterPro, STRING, and CDD all point to the same
function, the convergence score is high. When they disagree, it's low.
This mathematical backbone tells us HOW SURE we are about a prediction.
"""

from __future__ import annotations

import random
from typing import Any

from openlab.services.evidence_normalizer import NormalizedEvidence, normalize_evidence, normalize_payload


# Source-specific weights for convergence scoring.
# Function-predicting sources get high weight; context/noise sources get low.
CONVERGENCE_SOURCE_WEIGHTS: dict[str, float] = {
    # Function-predicting (high)
    "ncbi_blast": 2.0,
    "uniprot": 1.8,
    "interpro": 2.0,
    "eggnog": 1.8,
    "hhpred": 1.8,
    "pfam": 1.5,
    "foldseek": 1.5,
    "cdd": 1.8,
    "string": 1.0,
    "curated": 2.0,
    # Context sources (low — shouldn't dominate convergence)
    "genomic_neighborhood": 0.3,
    "literature": 0.2,
    "esmfold": 0.1,
    "deeptmhmm": 0.1,
    "signalp": 0.1,
    "alphafold": 0.3,
    "protein_features": 0.3,
    # Cancer evidence sources
    "clinvar": 1.8,
    "cosmic": 2.0,
    "oncokb": 2.0,
    "cbioportal": 1.5,
    "civic": 1.8,
    "tcga_gdc": 1.5,
}


def compute_convergence(evidence_list: list[dict[str, Any]]) -> float:
    """Compute convergence score from a list of evidence payloads.

    Each evidence dict must have at least a "source" key and any payload fields.
    Returns 0.0 (all disagree) to 1.0 (all agree).
    """
    if len(evidence_list) < 2:
        return 1.0 if evidence_list else 0.0

    # Normalize each evidence record
    normalized: list[tuple[dict, NormalizedEvidence]] = []
    for ev in evidence_list:
        norm = normalize_evidence(ev)
        if norm.go_terms or norm.ec_numbers or norm.categories or norm.keywords:
            normalized.append((ev, norm))

    if len(normalized) < 2:
        return 1.0 if normalized else 0.0

    total_weighted_sim = 0.0
    total_weight = 0.0

    for i in range(len(normalized)):
        ev_i, norm_i = normalized[i]
        w_i = _get_weight(ev_i)

        for j in range(i + 1, len(normalized)):
            ev_j, norm_j = normalized[j]
            w_j = _get_weight(ev_j)

            sim = _pairwise_agreement(norm_i, norm_j)
            pair_weight = w_i * w_j
            total_weighted_sim += sim * pair_weight
            total_weight += pair_weight

    if total_weight == 0:
        return 0.0

    score = total_weighted_sim / total_weight
    return round(max(0.0, min(1.0, score)), 3)


def bootstrap_stability(
    evidence_list: list[dict[str, Any]],
    n_iterations: int = 50,
    sample_fraction: float = 0.7,
) -> dict:
    """Assess convergence stability via bootstrap resampling.

    Resamples 70% of evidence 50 times, recomputes convergence each time.
    Stable predictions (std < 0.15) are robust.
    """
    if len(evidence_list) < 3:
        base = compute_convergence(evidence_list)
        return {
            "base_score": base, "mean": base, "std": 0.0,
            "ci_lower": base, "ci_upper": base,
            "n_iterations": 0, "stable": True,
        }

    base = compute_convergence(evidence_list)
    sample_size = max(2, int(len(evidence_list) * sample_fraction))
    scores: list[float] = []

    for _ in range(n_iterations):
        sample = random.sample(evidence_list, sample_size)
        scores.append(compute_convergence(sample))

    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std = variance ** 0.5

    scores_sorted = sorted(scores)
    ci_lower = scores_sorted[int(0.025 * len(scores_sorted))]
    ci_upper = scores_sorted[int(0.975 * len(scores_sorted))]

    return {
        "base_score": base,
        "mean": round(mean_score, 3),
        "std": round(std, 3),
        "ci_lower": round(ci_lower, 3),
        "ci_upper": round(ci_upper, 3),
        "n_iterations": n_iterations,
        "stable": std < 0.15,
    }


def classify_confidence_tier(
    convergence: float,
    consistency_passed: bool = True,
    ortholog_passed: bool | None = None,
) -> int:
    """Classify into confidence tier (1=High, 2=Moderate, 3=Low, 4=Flagged)."""
    if ortholog_passed is False:
        return 4
    if not consistency_passed and convergence < 0.1:
        return 4
    if convergence >= 0.5 and consistency_passed and ortholog_passed is not False:
        return 1
    if 0.2 <= convergence < 0.5 and (consistency_passed or ortholog_passed is True):
        return 2
    if convergence >= 0.5 and not consistency_passed:
        return 2
    return 3


# --- Internal helpers ---


def _get_weight(ev: dict) -> float:
    source = ev.get("source", "").lower()
    return CONVERGENCE_SOURCE_WEIGHTS.get(source, 0.5)


def _pairwise_agreement(a: NormalizedEvidence, b: NormalizedEvidence) -> float:
    """Multi-level agreement between two NormalizedEvidence records.

    Scoring layers (all always-on, weighted average):
      - GO term Jaccard × 3.0
      - EC number agreement × 2.0
      - Subcategory match (categories with ':') × 1.5
      - Broad category match (parent before ':') × 0.5
      - Keyword bigram overlap × 0.8
      - Keyword unigram Jaccard × 0.3
    """
    total_score = 0.0
    total_weight = 0.0

    # GO term Jaccard
    if a.go_terms or b.go_terms:
        if a.go_terms and b.go_terms:
            union = a.go_terms | b.go_terms
            jaccard = len(a.go_terms & b.go_terms) / len(union) if union else 0.0
        else:
            jaccard = 0.0
        total_score += jaccard * 3.0
        total_weight += 3.0

    # EC number agreement
    if a.ec_numbers or b.ec_numbers:
        if a.ec_numbers and b.ec_numbers:
            if a.ec_numbers & b.ec_numbers:
                ec_score = 1.0
            else:
                a_prefixes = {".".join(ec.split(".")[:3]) for ec in a.ec_numbers}
                b_prefixes = {".".join(ec.split(".")[:3]) for ec in b.ec_numbers}
                ec_score = 0.7 if a_prefixes & b_prefixes else 0.0
        else:
            ec_score = 0.0
        total_score += ec_score * 2.0
        total_weight += 2.0

    # Subcategory match (fine-grained, categories with ':')
    a_sub = {c for c in a.categories if ":" in c}
    b_sub = {c for c in b.categories if ":" in c}
    if a_sub or b_sub:
        if a_sub and b_sub:
            union = a_sub | b_sub
            jaccard = len(a_sub & b_sub) / len(union) if union else 0.0
        else:
            jaccard = 0.0
        total_score += jaccard * 1.5
        total_weight += 1.5

    # Broad category match (parent before ':')
    a_broad = {c.split(":")[0] for c in a.categories} if a.categories else set()
    b_broad = {c.split(":")[0] for c in b.categories} if b.categories else set()
    if a_broad or b_broad:
        if a_broad and b_broad:
            union = a_broad | b_broad
            jaccard = len(a_broad & b_broad) / len(union) if union else 0.0
        else:
            jaccard = 0.0
        total_score += jaccard * 0.5
        total_weight += 0.5

    # Keyword bigram overlap
    a_bigrams = _make_bigrams(a.keywords)
    b_bigrams = _make_bigrams(b.keywords)
    if a_bigrams or b_bigrams:
        if a_bigrams and b_bigrams:
            union = a_bigrams | b_bigrams
            jaccard = len(a_bigrams & b_bigrams) / len(union) if union else 0.0
        else:
            jaccard = 0.0
        total_score += jaccard * 0.8
        total_weight += 0.8

    # Keyword unigram Jaccard
    if a.keywords or b.keywords:
        if a.keywords and b.keywords:
            union = a.keywords | b.keywords
            jaccard = len(a.keywords & b.keywords) / len(union) if union else 0.0
        else:
            jaccard = 0.0
        total_score += jaccard * 0.3
        total_weight += 0.3

    return total_score / total_weight if total_weight > 0 else 0.0


def compute_convergence_from_orm(evidence_rows: list) -> float:
    """Compute convergence from ORM Evidence rows (DB-backed entry point).

    Used by DNASyn's gene_service for DB-backed convergence scoring.
    Same algorithm as compute_convergence but works with ORM objects.
    """
    if len(evidence_rows) < 2:
        return 1.0 if evidence_rows else 0.0

    normalized: list[tuple[Any, NormalizedEvidence]] = []
    for ev in evidence_rows:
        norm = normalize_evidence(ev)  # dispatches to ORM path with GO validation
        if norm.go_terms or norm.ec_numbers or norm.categories or norm.keywords:
            normalized.append((ev, norm))

    if len(normalized) < 2:
        return 1.0 if normalized else 0.0

    # ORM source weights (DNASyn naming convention)
    ORM_SOURCE_WEIGHTS = {
        "NCBI_BLAST": 2.0, "UniProt": 1.8, "InterProScan": 2.0,
        "eggNOG": 1.8, "HHpred": 1.8, "Pfam": 1.5, "Foldseek": 1.5,
        "STRING": 1.0, "CuratedReclassification": 2.0, "SynWiki": 1.5,
        "GenomicNeighborhood": 0.3, "operon_prediction": 0.3,
        "EuropePMC": 0.2, "ESMFold": 0.1, "DeepTMHMM": 0.1,
        "SignalP6": 0.1, "AlphaFold": 0.3, "PhylogeneticProfile": 0.5,
    }

    def _orm_weight(ev) -> float:
        source = (ev.payload or {}).get("source", "")
        return ORM_SOURCE_WEIGHTS.get(source, 0.5)

    total_weighted_sim = 0.0
    total_weight = 0.0

    for i in range(len(normalized)):
        ev_i, norm_i = normalized[i]
        w_i = _orm_weight(ev_i)

        for j in range(i + 1, len(normalized)):
            ev_j, norm_j = normalized[j]
            w_j = _orm_weight(ev_j)

            sim = _pairwise_agreement(norm_i, norm_j)
            pair_weight = w_i * w_j
            total_weighted_sim += sim * pair_weight
            total_weight += pair_weight

    if total_weight == 0:
        return 0.0

    return round(max(0.0, min(1.0, total_weighted_sim / total_weight)), 3)


def _make_bigrams(keywords: set[str]) -> set[str]:
    """Generate bigrams from sorted keywords for overlap comparison."""
    if len(keywords) < 2:
        return set()
    sorted_kw = sorted(keywords)
    return {f"{sorted_kw[i]}_{sorted_kw[i+1]}" for i in range(len(sorted_kw) - 1)}
