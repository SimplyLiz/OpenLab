"""Consensus variant classification.

Aggregates expert-curated classifications from multiple sources into a
single consensus classification. This is NOT de novo ACMG classification —
it aggregates existing expert assessments.

Trust hierarchy:
1. ClinVar expert-reviewed (3+ stars) — highest trust
2. OncoKB oncogenicity + level of evidence
3. CIViC evidence level A/B assertions
4. COSMIC frequency heuristic (high frequency = likely pathogenic)
5. Disagreement -> VUS with explanation
"""

from __future__ import annotations

import logging

from openlab.cancer.models.variant import (
    AnnotatedVariant,
    ClinicalSignificance,
)

logger = logging.getLogger(__name__)

# Classification weight by source and confidence
_SOURCE_TRUST: dict[str, float] = {
    "clinvar": 3.0,
    "oncokb": 2.5,
    "civic": 2.0,
    "cosmic": 1.0,
}

_PATHOGENIC_SCORES = {
    ClinicalSignificance.PATHOGENIC: 1.0,
    ClinicalSignificance.LIKELY_PATHOGENIC: 0.7,
    ClinicalSignificance.VUS: 0.0,
    ClinicalSignificance.LIKELY_BENIGN: -0.7,
    ClinicalSignificance.BENIGN: -1.0,
}


def classify_variant(annotated: AnnotatedVariant) -> AnnotatedVariant:
    """Apply consensus classification to an annotated variant.

    Modifies and returns the annotated variant with:
    - consensus_classification
    - confidence score
    - is_actionable flag
    """
    if not annotated.evidence:
        annotated.consensus_classification = ClinicalSignificance.VUS
        annotated.confidence = 0.0
        return annotated

    weighted_score = 0.0
    total_weight = 0.0
    has_actionable = False

    for ev in annotated.evidence:
        source_trust = _SOURCE_TRUST.get(ev.source, 0.5)
        weight = source_trust * max(ev.confidence, 0.1)

        if ev.classification is not None:
            path_score = _PATHOGENIC_SCORES.get(ev.classification, 0.0)
            weighted_score += path_score * weight
            total_weight += weight

        # Actionability from therapies
        if ev.therapies:
            has_actionable = True

    if total_weight > 0:
        consensus_score = weighted_score / total_weight

        if consensus_score >= 0.6:
            classification = ClinicalSignificance.PATHOGENIC
        elif consensus_score >= 0.3:
            classification = ClinicalSignificance.LIKELY_PATHOGENIC
        elif consensus_score <= -0.6:
            classification = ClinicalSignificance.BENIGN
        elif consensus_score <= -0.3:
            classification = ClinicalSignificance.LIKELY_BENIGN
        else:
            classification = ClinicalSignificance.VUS

        confidence = min(abs(consensus_score), 1.0)
    else:
        classification = ClinicalSignificance.VUS
        confidence = 0.0

    annotated.consensus_classification = classification
    annotated.confidence = round(confidence, 3)
    annotated.is_actionable = has_actionable or classification in (
        ClinicalSignificance.PATHOGENIC,
        ClinicalSignificance.LIKELY_PATHOGENIC,
    )

    return annotated


def classify_all(variants: list[AnnotatedVariant]) -> list[AnnotatedVariant]:
    """Apply consensus classification to all annotated variants."""
    return [classify_variant(v) for v in variants]
