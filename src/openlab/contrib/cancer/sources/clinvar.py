"""ClinVar variant-disease associations via NCBI E-utilities.

Queries ClinVar for pathogenic/likely-pathogenic variants associated with a gene,
focusing on cancer-related conditions. Uses the NCBI E-utilities esearch + esummary
pipeline with optional API key for higher rate limits (10 req/s vs 3).
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

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class ClinVarSource(CancerEvidenceSource):
    source_name = "clinvar"

    async def fetch(self, gene_symbol: str, http: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Search ClinVar for pathogenic variants in gene."""
        query = f"{gene_symbol}[gene] AND (pathogenic[clinsig] OR likely_pathogenic[clinsig])"

        params: dict[str, str] = {
            "db": "clinvar",
            "term": query,
            "retmax": "50",
            "retmode": "json",
        }
        _add_api_key(params)

        resp = await http.get(ESEARCH_URL, params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()

        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        # Fetch summaries
        summary_params: dict[str, str] = {
            "db": "clinvar",
            "id": ",".join(id_list[:50]),
            "retmode": "json",
        }
        _add_api_key(summary_params)

        resp = await http.get(ESUMMARY_URL, params=summary_params, timeout=15.0)
        resp.raise_for_status()
        summary_data = resp.json()

        results = []
        for uid in id_list[:50]:
            entry = summary_data.get("result", {}).get(uid, {})
            if not entry or isinstance(entry, str):
                continue
            results.append(self.normalize(entry))

        return results

    def normalize(self, raw: dict) -> dict[str, Any]:
        """Normalize ClinVar summary to standard format."""
        genes = raw.get("genes", [])
        gene_info = genes[0] if genes else {}

        clinical_sig = raw.get("clinical_significance", {})
        if isinstance(clinical_sig, dict):
            significance = clinical_sig.get("description", "")
        else:
            significance = str(clinical_sig)

        conditions = []
        for trait in raw.get("trait_set", []):
            if isinstance(trait, dict):
                conditions.append(trait.get("trait_name", ""))

        variation_set = raw.get("variation_set", [])
        variant_name = ""
        if variation_set and isinstance(variation_set[0], dict):
            variant_name = variation_set[0].get("variation_name", "")

        return {
            "source": "clinvar",
            "variant_id": str(raw.get("uid", "")),
            "variant_name": variant_name,
            "gene_symbol": gene_info.get("symbol", ""),
            "clinical_significance": significance,
            "conditions": conditions,
            "review_status": raw.get("review_status", ""),
            "title": raw.get("title", ""),
            "categories": _classify_significance(significance),
            "_sources": [f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{raw.get('uid', '')}"],
        }


def _classify_significance(sig: str) -> list[str]:
    """Map clinical significance to cancer-relevant categories."""
    cats = []
    sig_lower = sig.lower()
    if "pathogenic" in sig_lower:
        cats.append("cancer:pathogenic_variant")
    if "likely pathogenic" in sig_lower:
        cats.append("cancer:likely_pathogenic")
    if "drug response" in sig_lower:
        cats.append("cancer:drug_target")
    if "risk factor" in sig_lower:
        cats.append("cancer:risk_factor")
    return cats


def _add_api_key(params: dict) -> None:
    """Add NCBI API key if configured."""
    try:
        from openlab.config import config
        if config.ncbi.api_key:
            params["api_key"] = config.ncbi.api_key
    except Exception:
        pass


async def search_clinvar(http: httpx.AsyncClient, gene_symbol: str) -> dict:
    """Async entry point for agent tools."""
    source = ClinVarSource()
    try:
        variants = await source.fetch_with_retry(gene_symbol, http)
        return {
            "source": "clinvar",
            "gene_symbol": gene_symbol,
            "variants": variants,
            "total": len(variants),
            "_sources": [f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene_symbol}%5Bgene%5D"],
        }
    except Exception as e:
        logger.warning("ClinVar search failed for %s: %s", gene_symbol, e)
        return {"source": "clinvar", "gene_symbol": gene_symbol, "variants": [], "total": 0}


def run_clinvar(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: search ClinVar for each gene."""
    import asyncio
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "clinvar"):
            continue
        if not gene.name:
            continue

        try:
            async_http = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
            try:
                variants = asyncio.run(ClinVarSource().fetch_with_retry(gene.name, async_http))
            finally:
                asyncio.run(async_http.aclose())

            if not variants:
                continue

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("clinvar"),
                payload={
                    "source": "ClinVar",
                    "variants": variants,
                    "total": len(variants),
                },
                source_ref="clinvar",
                confidence=0.7,
            )
            count += 1
            logger.info("ClinVar %s: %d variants", gene.name, len(variants))
        except Exception as e:
            logger.warning("ClinVar %s error: %s", gene.name, e)

    return count
