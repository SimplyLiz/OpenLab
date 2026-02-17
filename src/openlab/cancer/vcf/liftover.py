"""Genome coordinate liftover between hg19 and hg38.

Uses pyliftover when available; falls back to a no-op passthrough
with a warning if the library is not installed.
"""

from __future__ import annotations

import logging
from typing import Any

from openlab.cancer.models.variant import GenomeBuild, VariantRecord

logger = logging.getLogger(__name__)

_liftover_cache: dict[str, object] = {}


def liftover_variant(
    variant: VariantRecord,
    from_build: GenomeBuild,
    to_build: GenomeBuild,
) -> VariantRecord | None:
    """Liftover a variant from one genome build to another.

    Returns a new VariantRecord with updated coordinates, or None if liftover fails.
    """
    if from_build == to_build:
        return variant

    if from_build.is_hg38() == to_build.is_hg38():
        # Same assembly, just different naming convention
        return variant

    try:
        from pyliftover import LiftOver  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("pyliftover not installed; skipping coordinate liftover")
        return variant

    chain_key = f"{from_build.value}_to_{to_build.value}"
    if chain_key not in _liftover_cache:
        if from_build.is_hg19() and to_build.is_hg38():
            _liftover_cache[chain_key] = LiftOver("hg19", "hg38")
        elif from_build.is_hg38() and to_build.is_hg19():
            _liftover_cache[chain_key] = LiftOver("hg38", "hg19")
        else:
            logger.warning("Unsupported liftover: %s -> %s", from_build, to_build)
            return None

    lo: Any = _liftover_cache[chain_key]

    chrom = variant.chrom
    if not chrom.startswith("chr"):
        chrom = f"chr{chrom}"

    results = lo.convert_coordinate(chrom, variant.pos - 1)  # pyliftover is 0-based
    if not results:
        logger.debug("Liftover failed for %s:%d", variant.chrom, variant.pos)
        return None

    new_chrom, new_pos, strand, _ = results[0]
    new_chrom = new_chrom.replace("chr", "")

    return variant.model_copy(update={
        "chrom": new_chrom,
        "pos": new_pos + 1,  # back to 1-based
    })
