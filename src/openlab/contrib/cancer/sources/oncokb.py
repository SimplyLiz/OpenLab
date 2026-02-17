"""OncoKB precision oncology knowledge base.

Queries the OncoKB REST API v1 for gene-level oncogenicity data,
actionable mutations, and therapeutic implications. Requires a Bearer
token (free for academic use, register at oncokb.org).
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

ONCOKB_API = "https://www.oncokb.org/api/v1"


class OncoKBSource(CancerEvidenceSource):
    source_name = "oncokb"

    async def fetch(self, gene_symbol: str, http: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch gene info and variants from OncoKB."""
        headers = _get_auth_headers()

        # Gene-level query
        resp = await http.get(
            f"{ONCOKB_API}/genes/lookup",
            params={"query": gene_symbol},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        gene_data = resp.json()

        if not gene_data:
            return []

        # Get variants for the gene
        resp = await http.get(
            f"{ONCOKB_API}/variants/lookup",
            params={"hugoSymbol": gene_symbol},
            headers=headers,
            timeout=15.0,
        )
        resp.raise_for_status()
        variants_data = resp.json()

        results = []
        # Normalize gene-level info
        if isinstance(gene_data, list):
            for g in gene_data:
                results.append(self._normalize_gene(g))
        elif isinstance(gene_data, dict):
            results.append(self._normalize_gene(gene_data))

        # Normalize variants
        if isinstance(variants_data, list):
            for v in variants_data[:50]:
                results.append(self.normalize(v))

        return results

    def _normalize_gene(self, raw: dict) -> dict[str, Any]:
        """Normalize OncoKB gene info."""
        oncogene = raw.get("oncogene", False)
        tsg = raw.get("tsg", False)

        categories = []
        if oncogene:
            categories.append("cancer:oncogene")
        if tsg:
            categories.append("cancer:tumor_suppressor")

        return {
            "source": "oncokb",
            "record_type": "gene",
            "hugo_symbol": raw.get("hugoSymbol", ""),
            "entrez_gene_id": raw.get("entrezGeneId", ""),
            "oncogene": oncogene,
            "tumor_suppressor": tsg,
            "categories": categories,
            "_sources": [f"https://www.oncokb.org/gene/{raw.get('hugoSymbol', '')}"],
        }

    def normalize(self, raw: dict) -> dict[str, Any]:
        """Normalize OncoKB variant entry."""
        gene = raw.get("gene", {}) or {}
        consequence = raw.get("consequence", {}) or {}

        categories = ["cancer:actionable_variant"]
        mutation_effect = raw.get("mutationEffect", {}) or {}
        effect = mutation_effect.get("knownEffect", "")
        if "gain" in effect.lower():
            categories.append("mutation:gain_of_function")
        elif "loss" in effect.lower():
            categories.append("mutation:loss_of_function")

        oncogenic = raw.get("oncogenic", "")
        if "oncogenic" in str(oncogenic).lower():
            categories.append("cancer:oncogenic")

        return {
            "source": "oncokb",
            "record_type": "variant",
            "hugo_symbol": gene.get("hugoSymbol", ""),
            "variant_name": raw.get("name", "") or raw.get("alteration", ""),
            "oncogenic": oncogenic,
            "mutation_effect": effect,
            "consequence_type": consequence.get("term", ""),
            "categories": categories,
            "_sources": [f"https://www.oncokb.org/gene/{gene.get('hugoSymbol', '')}"],
        }


def _get_auth_headers() -> dict[str, str]:
    """Get OncoKB auth headers from config."""
    try:
        from openlab.config import config
        token = config.cancer.oncokb_token if hasattr(config, "cancer") else ""
        if token:
            return {"Authorization": f"Bearer {token}"}
    except Exception:
        pass
    return {}


async def search_oncokb(http: httpx.AsyncClient, gene_symbol: str) -> dict:
    """Async entry point for agent tools."""
    source = OncoKBSource()
    try:
        entries = await source.fetch_with_retry(gene_symbol, http)
        return {
            "source": "oncokb",
            "gene_symbol": gene_symbol,
            "entries": entries,
            "total": len(entries),
            "_sources": [f"https://www.oncokb.org/gene/{gene_symbol}"],
        }
    except Exception as e:
        logger.warning("OncoKB search failed for %s: %s", gene_symbol, e)
        return {"source": "oncokb", "gene_symbol": gene_symbol, "entries": [], "total": 0}


def run_oncokb(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: query OncoKB for each gene."""
    import asyncio
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "oncokb"):
            continue
        if not gene.name:
            continue

        try:
            async_http = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
            try:
                entries = asyncio.run(OncoKBSource().fetch_with_retry(gene.name, async_http))
            finally:
                asyncio.run(async_http.aclose())

            if not entries:
                continue

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("oncokb"),
                payload={
                    "source": "OncoKB",
                    "entries": entries,
                    "total": len(entries),
                },
                source_ref="oncokb",
                confidence=0.8,
            )
            count += 1
            logger.info("OncoKB %s: %d entries", gene.name, len(entries))
        except Exception as e:
            logger.warning("OncoKB %s error: %s", gene.name, e)

    return count
