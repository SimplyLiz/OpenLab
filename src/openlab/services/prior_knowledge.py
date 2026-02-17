"""Prior knowledge service — loads DNASyn findings for pre-populating gene predictions.

Merges two sources:
  1. confidence_tiers.json — 128 graduated genes from the DNASyn evidence pipeline
  2. curated_reclassifications.yaml — 16 expert-curated assignments from published research

Curated assignments take priority over pipeline predictions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class PriorPrediction:
    """A pre-existing prediction for a gene from DNASyn."""
    locus_tag: str
    proposed_function: str
    confidence_score: float
    convergence_score: float
    evidence_count: int
    tier: int
    source: str  # "dnasyn_pipeline" or "curated:<paper>"
    method: str  # computational method used


def _load_confidence_tiers() -> dict[str, PriorPrediction]:
    """Load graduated genes from DNASyn's confidence_tiers.json."""
    path = DATA_DIR / "confidence_tiers.json"
    if not path.exists():
        logger.warning(f"confidence_tiers.json not found at {path}")
        return {}

    data = json.loads(path.read_text())
    predictions: dict[str, PriorPrediction] = {}

    for tier_num, genes in data.get("tiers", {}).items():
        for g in genes:
            tag = g["locus_tag"]
            predictions[tag] = PriorPrediction(
                locus_tag=tag,
                proposed_function=g["proposed_function"],
                confidence_score=g.get("confidence_score", 0.5),
                convergence_score=g.get("convergence_score", 0.0),
                evidence_count=g.get("evidence_count", 0),
                tier=int(tier_num),
                source="dnasyn_pipeline",
                method="multi-source evidence convergence + LLM synthesis",
            )

    return predictions


def _load_curated() -> dict[str, PriorPrediction]:
    """Load curated reclassifications from published research."""
    path = DATA_DIR / "curated_reclassifications.yaml"
    if not path.exists():
        logger.warning(f"curated_reclassifications.yaml not found at {path}")
        return {}

    data = yaml.safe_load(path.read_text())
    predictions: dict[str, PriorPrediction] = {}

    for entry in data.get("reclassifications", []):
        tag = entry["locus_tag"]
        predictions[tag] = PriorPrediction(
            locus_tag=tag,
            proposed_function=entry["predicted_function"],
            confidence_score=entry.get("confidence", 0.8),
            convergence_score=0.0,  # curated don't have convergence scores
            evidence_count=1,
            tier=1,  # curated = highest confidence
            source=f"curated:{entry.get('source', 'unknown')}",
            method=entry.get("method", "expert curation"),
        )

    return predictions


# Module-level cache
_cache: dict[str, PriorPrediction] | None = None


def get_prior_knowledge() -> dict[str, PriorPrediction]:
    """Get all prior predictions, keyed by locus_tag.

    Curated assignments override pipeline predictions.
    """
    global _cache
    if _cache is not None:
        return _cache

    # Pipeline first, then curated overrides
    predictions = _load_confidence_tiers()
    curated = _load_curated()
    predictions.update(curated)  # curated wins

    _cache = predictions
    logger.info(
        f"Loaded {len(predictions)} prior predictions "
        f"({len(curated)} curated, {len(predictions) - len(curated)} from pipeline)"
    )
    return predictions


def lookup(locus_tag: str) -> PriorPrediction | None:
    """Look up prior knowledge for a single gene."""
    return get_prior_knowledge().get(locus_tag)
