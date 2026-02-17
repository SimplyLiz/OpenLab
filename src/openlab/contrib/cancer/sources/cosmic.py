"""COSMIC somatic mutation catalogue via Clinical Tables API.

Queries the NLM Clinical Tables API (open, no auth required) which provides
COSMIC mutation data. For full COSMIC data, academic registration is required
via the COSMIC website, but the Clinical Tables endpoint is freely accessible.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from openlab.contrib.cancer.sources.base import CancerEvidenceSource
from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

# NLM Clinical Tables API — public COSMIC subset
CLINICAL_TABLES_URL = "https://clinicaltables.nlm.nih.gov/api/cosmic/v4/search"


class CosmicSource(CancerEvidenceSource):
    source_name = "cosmic"

    async def fetch(self, gene_symbol: str, http: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Search COSMIC mutations for gene via Clinical Tables API."""
        resp = await http.get(
            CLINICAL_TABLES_URL,
            params={
                "terms": gene_symbol,
                "maxList": "50",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Clinical Tables returns [total, codes, extras, display_strings]
        if not isinstance(data, list) or len(data) < 4:
            return []

        total = data[0]
        codes = data[1] if len(data) > 1 else []
        display_strings = data[3] if len(data) > 3 else []

        results = []
        for i, code in enumerate(codes):
            display = display_strings[i] if i < len(display_strings) else []
            results.append(self.normalize({
                "code": code,
                "display": display,
                "gene_symbol": gene_symbol,
                "total_in_db": total,
            }))

        return results

    def normalize(self, raw: dict) -> dict[str, Any]:
        """Normalize COSMIC Clinical Tables entry."""
        display = raw.get("display", [])

        # Display fields: [mutation_id, gene, cds_mutation, aa_mutation, primary_site, ...]
        mutation_id = display[0] if len(display) > 0 else raw.get("code", "")
        gene = display[1] if len(display) > 1 else raw.get("gene_symbol", "")
        cds_mutation = display[2] if len(display) > 2 else ""
        aa_mutation = display[3] if len(display) > 3 else ""
        primary_site = display[4] if len(display) > 4 else ""
        histology = display[5] if len(display) > 5 else ""

        categories = ["cancer:somatic_mutation"]
        if aa_mutation:
            if "Missense" in str(aa_mutation) or "p." in str(aa_mutation):
                categories.append("mutation:missense")
            if "Nonsense" in str(aa_mutation) or "*" in str(aa_mutation):
                categories.append("mutation:loss_of_function")

        return {
            "source": "cosmic",
            "mutation_id": str(mutation_id),
            "gene_symbol": str(gene),
            "cds_mutation": str(cds_mutation),
            "aa_mutation": str(aa_mutation),
            "primary_site": str(primary_site),
            "histology": str(histology),
            "categories": categories,
            "_sources": [f"https://cancer.sanger.ac.uk/cosmic/gene/analysis?ln={gene}"],
        }


async def search_cosmic(http: httpx.AsyncClient, gene_symbol: str) -> dict:
    """Async entry point for agent tools."""
    source = CosmicSource()
    try:
        mutations = await source.fetch_with_retry(gene_symbol, http)
        return {
            "source": "cosmic",
            "gene_symbol": gene_symbol,
            "mutations": mutations,
            "total": len(mutations),
            "_sources": [f"https://cancer.sanger.ac.uk/cosmic/gene/analysis?ln={gene_symbol}"],
        }
    except Exception as e:
        logger.warning("COSMIC search failed for %s: %s", gene_symbol, e)
        return {"source": "cosmic", "gene_symbol": gene_symbol, "mutations": [], "total": 0}


def run_cosmic(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: search COSMIC for each gene."""
    import asyncio
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "cosmic"):
            continue
        if not gene.name:
            continue

        try:
            async_http = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
            try:
                mutations = asyncio.run(CosmicSource().fetch_with_retry(gene.name, async_http))
            finally:
                asyncio.run(async_http.aclose())

            if not mutations:
                continue

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("cosmic"),
                payload={
                    "source": "COSMIC",
                    "mutations": mutations,
                    "total": len(mutations),
                },
                source_ref="cosmic",
                confidence=0.7,
            )
            count += 1
            logger.info("COSMIC %s: %d mutations", gene.name, len(mutations))
        except Exception as e:
            logger.warning("COSMIC %s error: %s", gene.name, e)

    return count
