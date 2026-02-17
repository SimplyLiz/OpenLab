"""TCGA/GDC — NCI Genomic Data Commons REST API.

Queries the GDC public API for somatic mutation frequencies and case counts
across TCGA cancer projects. No authentication required. Open data.
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

GDC_API = "https://api.gdc.cancer.gov"


class TcgaGdcSource(CancerEvidenceSource):
    source_name = "tcga_gdc"

    async def fetch(self, gene_symbol: str, http: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch mutation frequency data from GDC for a gene."""
        # Query SSM occurrences filtered by gene symbol
        filters = {
            "op": "and",
            "content": [
                {
                    "op": "in",
                    "content": {
                        "field": "consequence.transcript.gene.symbol",
                        "value": [gene_symbol],
                    },
                },
                {
                    "op": "in",
                    "content": {
                        "field": "consequence.transcript.consequence_type",
                        "value": [
                            "missense_variant",
                            "stop_gained",
                            "frameshift_variant",
                            "splice_donor_variant",
                            "splice_acceptor_variant",
                        ],
                    },
                },
            ],
        }

        import json
        resp = await http.get(
            f"{GDC_API}/ssms",
            params={
                "filters": json.dumps(filters),
                "fields": (
                    "ssm_id,genomic_dna_change,consequence.transcript.gene.symbol,"
                    "consequence.transcript.consequence_type,"
                    "consequence.transcript.aa_change,"
                    "occurrence.case.project.project_id"
                ),
                "size": "50",
                "format": "json",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        hits = data.get("data", {}).get("hits", [])
        results = []
        for hit in hits:
            results.append(self.normalize(hit))

        return results

    def normalize(self, raw: dict) -> dict[str, Any]:
        """Normalize a GDC SSM hit."""
        consequences = raw.get("consequence", [])
        gene_symbol = ""
        aa_change = ""
        consequence_type = ""

        if consequences:
            transcript = consequences[0].get("transcript", {})
            gene_info = transcript.get("gene", {})
            gene_symbol = gene_info.get("symbol", "")
            aa_change = transcript.get("aa_change", "")
            consequence_type = transcript.get("consequence_type", "")

        # Count unique projects from occurrences
        occurrences = raw.get("occurrence", [])
        projects = set()
        for occ in occurrences:
            case = occ.get("case", {})
            project = case.get("project", {})
            pid = project.get("project_id", "")
            if pid:
                projects.add(pid)

        categories = ["cancer:somatic_mutation"]
        if consequence_type:
            ct_lower = consequence_type.lower()
            if "missense" in ct_lower:
                categories.append("mutation:missense")
            elif "stop_gained" in ct_lower or "frameshift" in ct_lower:
                categories.append("mutation:loss_of_function")
            elif "splice" in ct_lower:
                categories.append("mutation:splice")

        return {
            "source": "tcga_gdc",
            "ssm_id": raw.get("ssm_id", ""),
            "gene_symbol": gene_symbol,
            "genomic_dna_change": raw.get("genomic_dna_change", ""),
            "aa_change": aa_change,
            "consequence_type": consequence_type,
            "project_count": len(projects),
            "projects": sorted(projects),
            "case_count": len(occurrences),
            "categories": categories,
            "_sources": [f"https://portal.gdc.cancer.gov/ssms/{raw.get('ssm_id', '')}"],
        }


async def search_tcga_gdc(http: httpx.AsyncClient, gene_symbol: str) -> dict:
    """Async entry point for agent tools."""
    source = TcgaGdcSource()
    try:
        mutations = await source.fetch_with_retry(gene_symbol, http)
        return {
            "source": "tcga_gdc",
            "gene_symbol": gene_symbol,
            "mutations": mutations,
            "total": len(mutations),
            "_sources": [f"https://portal.gdc.cancer.gov/genes/{gene_symbol}"],
        }
    except Exception as e:
        logger.warning("TCGA/GDC search failed for %s: %s", gene_symbol, e)
        return {"source": "tcga_gdc", "gene_symbol": gene_symbol, "mutations": [], "total": 0}


def run_tcga_gdc(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: query GDC for each gene."""
    import asyncio
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "tcga_gdc"):
            continue
        if not gene.name:
            continue

        try:
            async_http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            try:
                mutations = asyncio.run(TcgaGdcSource().fetch_with_retry(gene.name, async_http))
            finally:
                asyncio.run(async_http.aclose())

            if not mutations:
                continue

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("tcga_gdc"),
                payload={
                    "source": "TCGA_GDC",
                    "mutations": mutations,
                    "total": len(mutations),
                },
                source_ref="tcga_gdc",
                confidence=0.6,
            )
            count += 1
            logger.info("TCGA/GDC %s: %d mutations", gene.name, len(mutations))
        except Exception as e:
            logger.warning("TCGA/GDC %s error: %s", gene.name, e)

    return count
