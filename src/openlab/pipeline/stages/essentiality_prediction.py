"""Stage: Essentiality Prediction — heuristic gene essentiality from DNAView.

Pure function: checks product annotation, EC numbers, gene class.
No network calls.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from openlab.models import GenomeRecord, PipelineEvent, StageStatus

logger = logging.getLogger(__name__)

STAGE = "essentiality_prediction"


def predict_essentiality(gene_data: dict) -> bool:
    """Predict gene essentiality based on annotations.

    Conservative heuristic — unknown genes are assumed essential.
    """
    classification = gene_data.get("classification", "unknown")
    product = (gene_data.get("product", "") or "").lower()
    ec = gene_data.get("ec_number", "")
    category = gene_data.get("functional_category", "unknown")

    # Unknown genes assumed essential (conservative)
    if classification == "unknown" or category == "unknown":
        return True

    # Ribosomal proteins
    if "ribosomal" in product:
        return True

    # DNA/RNA polymerase, primase, helicase, ligase
    if any(kw in product for kw in ["polymerase", "primase", "helicase", "ligase"]):
        return True

    # tRNA synthetases
    if "trna" in product and ("synthetase" in product or "ligase" in product):
        return True

    # Cell division proteins
    if any(kw in product for kw in ["ftsz", "division", "septum"]):
        return True

    # Core metabolic enzymes
    if ec and any(ec.startswith(prefix) for prefix in ["2.7.1", "1.2.1", "5.4.2", "4.1.2"]):
        return True

    # Hypothetical proteins without function
    if "hypothetical" in product and classification != "known":
        return True

    return False


async def run(genome: GenomeRecord) -> AsyncGenerator[PipelineEvent, None]:
    """Run essentiality prediction for all genes in a genome."""
    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.0,
        data={"message": "Predicting gene essentiality..."},
    )

    predictions: dict[str, bool] = {}
    total_essential = 0
    total_nonessential = 0

    for i, gene in enumerate(genome.genes):
        is_essential = predict_essentiality({
            "classification": "known" if gene.functional_category not in ("unknown", "predicted") else "unknown",
            "product": gene.product,
            "ec_number": "",
            "functional_category": gene.functional_category,
        })
        predictions[gene.locus_tag] = is_essential
        gene.is_essential = is_essential

        if is_essential:
            total_essential += 1
        else:
            total_nonessential += 1

    logger.info(f"Essentiality: {total_essential} essential, {total_nonessential} non-essential")

    yield PipelineEvent(
        stage=STAGE,
        status=StageStatus.COMPLETED,
        progress=1.0,
        data={
            "total_essential": total_essential,
            "total_nonessential": total_nonessential,
            "predictions": predictions,
        },
    )
