"""cBioPortal cancer genomics — open REST API.

Queries the cBioPortal public REST API for mutation data across cancer studies.
No authentication required. Rate limit ~10 req/s.
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

CBIOPORTAL_API = "https://www.cbioportal.org/api"


class CBioPortalSource(CancerEvidenceSource):
    source_name = "cbioportal"

    async def fetch(self, gene_symbol: str, http: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch mutation data from cBioPortal for a gene."""
        # Get gene metadata
        resp = await http.get(
            f"{CBIOPORTAL_API}/genes/{gene_symbol}",
            headers={"Accept": "application/json"},
            timeout=15.0,
        )
        resp.raise_for_status()
        gene_data = resp.json()

        entrez_id = gene_data.get("entrezGeneId")
        if not entrez_id:
            return []

        # Get mutations across all studies
        resp = await http.get(
            f"{CBIOPORTAL_API}/mutations",
            params={
                "entrezGeneId": str(entrez_id),
                "projection": "SUMMARY",
                "pageSize": "50",
                "pageNumber": "0",
                "direction": "ASC",
            },
            headers={"Accept": "application/json"},
            timeout=30.0,
        )
        resp.raise_for_status()
        mutations = resp.json()

        results = []
        for mut in mutations[:50]:
            results.append(self.normalize(mut))

        return results

    def normalize(self, raw: dict) -> dict[str, Any]:
        """Normalize cBioPortal mutation entry."""
        gene = raw.get("gene", {}) or {}
        mutation_type = raw.get("mutationType", "")

        categories = ["cancer:somatic_mutation"]
        if mutation_type:
            mt_lower = mutation_type.lower()
            if "missense" in mt_lower:
                categories.append("mutation:missense")
            elif any(k in mt_lower for k in ("nonsense", "stop", "frame_shift", "frameshift")):
                categories.append("mutation:loss_of_function")
            elif "splice" in mt_lower:
                categories.append("mutation:splice")
            elif "in_frame" in mt_lower:
                categories.append("mutation:in_frame")

        return {
            "source": "cbioportal",
            "mutation_id": raw.get("uniqueMutationId", ""),
            "hugo_symbol": gene.get("hugoGeneSymbol", ""),
            "entrez_gene_id": gene.get("entrezGeneId", ""),
            "protein_change": raw.get("proteinChange", ""),
            "mutation_type": mutation_type,
            "study_id": raw.get("molecularProfileId", ""),
            "sample_id": raw.get("sampleId", ""),
            "cancer_type": raw.get("cancerType", ""),
            "validation_status": raw.get("validationStatus", ""),
            "categories": categories,
            "_sources": ["https://www.cbioportal.org"],
        }


async def search_cbioportal(http: httpx.AsyncClient, gene_symbol: str) -> dict:
    """Async entry point for agent tools."""
    source = CBioPortalSource()
    try:
        mutations = await source.fetch_with_retry(gene_symbol, http)
        return {
            "source": "cbioportal",
            "gene_symbol": gene_symbol,
            "mutations": mutations,
            "total": len(mutations),
            "_sources": [f"https://www.cbioportal.org/results/mutations?gene_list={gene_symbol}"],
        }
    except Exception as e:
        logger.warning("cBioPortal search failed for %s: %s", gene_symbol, e)
        return {"source": "cbioportal", "gene_symbol": gene_symbol, "mutations": [], "total": 0}


def run_cbioportal(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: query cBioPortal for each gene."""
    import asyncio
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "cbioportal"):
            continue
        if not gene.name:
            continue

        try:
            async_http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            try:
                mutations = asyncio.run(CBioPortalSource().fetch_with_retry(gene.name, async_http))
            finally:
                asyncio.run(async_http.aclose())

            if not mutations:
                continue

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("cbioportal"),
                payload={
                    "source": "cBioPortal",
                    "mutations": mutations,
                    "total": len(mutations),
                },
                source_ref="cbioportal",
                confidence=0.6,
            )
            count += 1
            logger.info("cBioPortal %s: %d mutations", gene.name, len(mutations))
        except Exception as e:
            logger.warning("cBioPortal %s error: %s", gene.name, e)

    return count
