"""Stage: Kinetics Enrichment — fetch kinetic parameters via waterfall ETL."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

import httpx

from openlab.config import config
from openlab.models import GenomeRecord, KineticsEntry, PipelineEvent, StageStatus
from openlab.services.etl.disk_cache import DiskCache
from openlab.services.etl.brenda import AsyncBRENDAClient
from openlab.services.etl.sabio_rk import AsyncSabioRKClient
from openlab.services.etl.datanator import AsyncDatanatorClient
from openlab.services.etl.kinetics_fetch import fetch_kinetics_for_ec, compute_coverage

logger = logging.getLogger(__name__)

STAGE = "kinetics_enrichment"


async def run(
    genome: GenomeRecord,
    http: httpx.AsyncClient,
) -> AsyncGenerator[PipelineEvent, None]:
    """Fetch kinetic parameters for all genes with EC numbers."""
    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.0,
        data={"message": "Enriching kinetic parameters..."},
    )

    cache = DiskCache(config.etl.cache_dir)
    etl = config.etl

    brenda = AsyncBRENDAClient(http, cache, etl.brenda_email, etl.brenda_password, etl.brenda_rate) if etl.enable_brenda else None
    sabio = AsyncSabioRKClient(http, cache, etl.sabio_rate) if etl.enable_sabio else None
    datanator = AsyncDatanatorClient(http, cache, etl.datanator_rate) if etl.enable_datanator else None

    # Collect genes with EC numbers (from predictions or annotations)
    ec_genes: list[tuple[str, str]] = []  # (locus_tag, ec_number)
    for gene in genome.genes:
        # Check if gene has an EC from prior knowledge / functional prediction
        # EC numbers can come from evidence records — for now check product annotation
        ec = _extract_ec_from_product(gene.product)
        if ec:
            ec_genes.append((gene.locus_tag, ec))

    total = len(ec_genes)
    kinetics_list: list[KineticsEntry] = []
    measured_count = 0
    assumed_count = 0

    for i, (locus_tag, ec) in enumerate(ec_genes):
        try:
            entry = await fetch_kinetics_for_ec(
                ec_number=ec,
                reaction_id=f"rxn_{locus_tag}",
                brenda=brenda,
                sabio=sabio,
                datanator=datanator,
            )
            kinetics_list.append(entry)

            trust = entry.kcat.provenance.trust_level.value
            if trust in ("measured", "measuredHomolog"):
                measured_count += 1
            elif trust == "assumed":
                assumed_count += 1
        except Exception as e:
            logger.warning(f"Kinetics fetch failed for {locus_tag} EC {ec}: {e}")

        if (i + 1) % 5 == 0 or i == total - 1:
            done = i + 1
            measured_pct = round(measured_count / max(done, 1) * 100, 1)
            assumed_pct = round(assumed_count / max(done, 1) * 100, 1)
            yield PipelineEvent(
                stage=STAGE, status=StageStatus.RUNNING,
                progress=done / max(total, 1),
                data={
                    "done": done, "total": total,
                    "measured_pct": measured_pct, "assumed_pct": assumed_pct,
                },
            )

    coverage = compute_coverage(kinetics_list)

    yield PipelineEvent(
        stage=STAGE,
        status=StageStatus.COMPLETED,
        progress=1.0,
        data={
            "coverage_report": coverage,
            "total_reactions": len(kinetics_list),
            "kinetics": [k.model_dump() for k in kinetics_list],
        },
    )


def _extract_ec_from_product(product: str) -> str:
    """Extract EC number from product annotation string."""
    import re
    if not product:
        return ""
    # Match patterns like "EC 1.2.3.4" or "(EC:1.2.3.4)" or just "1.2.3.4"
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", product)
    return m.group(1) if m else ""
