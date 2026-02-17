"""CIViC — Clinical Interpretation of Variants in Cancer (CC0 licensed).

Queries the CIViC GraphQL API for curated clinical evidence items
linking gene variants to cancer diagnoses, therapies, and prognoses.
No authentication required. CC0 public domain data.
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

CIVIC_GRAPHQL_URL = "https://civicdb.org/api/graphql"

GENE_QUERY = """
query GeneSearch($name: String!) {
  genes(name: $name) {
    nodes {
      id
      name
      description
      officialName
      variants {
        totalCount
        nodes {
          id
          name
          singleVariantMolecularProfileId
          variantTypes {
            name
          }
        }
      }
      evidenceItems {
        totalCount
        nodes {
          id
          status
          evidenceType
          evidenceLevel
          evidenceDirection
          significance
          description
          therapies {
            name
          }
          disease {
            name
            doid
          }
          source {
            citationId
            sourceType
          }
        }
      }
    }
  }
}
"""


class CIViCSource(CancerEvidenceSource):
    source_name = "civic"

    async def fetch(self, gene_symbol: str, http: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch CIViC gene data via GraphQL."""
        resp = await http.post(
            CIVIC_GRAPHQL_URL,
            json={"query": GENE_QUERY, "variables": {"name": gene_symbol}},
            headers={"Content-Type": "application/json"},
            timeout=20.0,
        )
        resp.raise_for_status()
        data = resp.json()

        genes = data.get("data", {}).get("genes", {}).get("nodes", [])
        if not genes:
            return []

        gene = genes[0]
        results = []

        # Gene-level record
        results.append({
            "source": "civic",
            "record_type": "gene",
            "civic_id": gene.get("id"),
            "name": gene.get("name", ""),
            "description": gene.get("description", ""),
            "official_name": gene.get("officialName", ""),
            "variant_count": gene.get("variants", {}).get("totalCount", 0),
            "evidence_count": gene.get("evidenceItems", {}).get("totalCount", 0),
            "categories": ["cancer:curated_evidence"],
            "_sources": [f"https://civicdb.org/genes/{gene.get('id', '')}"],
        })

        # Evidence items
        for ev in gene.get("evidenceItems", {}).get("nodes", [])[:50]:
            results.append(self.normalize(ev))

        return results

    def normalize(self, raw: dict) -> dict[str, Any]:
        """Normalize a CIViC evidence item."""
        therapies = [t.get("name", "") for t in (raw.get("therapies") or [])]
        disease = raw.get("disease") or {}
        source = raw.get("source") or {}

        categories = ["cancer:curated_evidence"]
        ev_type = raw.get("evidenceType", "")
        if ev_type == "PREDICTIVE":
            categories.append("cancer:drug_target")
        elif ev_type == "DIAGNOSTIC":
            categories.append("cancer:diagnostic_marker")
        elif ev_type == "PROGNOSTIC":
            categories.append("cancer:prognostic_marker")
        elif ev_type == "PREDISPOSING":
            categories.append("cancer:risk_factor")

        significance = raw.get("significance", "")
        if significance and "SENSITIV" in str(significance).upper():
            categories.append("cancer:drug_sensitive")
        elif significance and "RESIST" in str(significance).upper():
            categories.append("cancer:drug_resistant")

        pmid = ""
        if source.get("sourceType") == "PUBMED":
            pmid = str(source.get("citationId", ""))

        return {
            "source": "civic",
            "record_type": "evidence",
            "evidence_id": raw.get("id"),
            "evidence_type": ev_type,
            "evidence_level": raw.get("evidenceLevel", ""),
            "evidence_direction": raw.get("evidenceDirection", ""),
            "significance": significance,
            "description": raw.get("description", ""),
            "disease_name": disease.get("name", ""),
            "disease_doid": disease.get("doid", ""),
            "therapies": therapies,
            "pmid": pmid,
            "status": raw.get("status", ""),
            "categories": categories,
            "_sources": [f"https://civicdb.org/evidence/{raw.get('id', '')}"],
        }


async def search_civic(http: httpx.AsyncClient, gene_symbol: str) -> dict:
    """Async entry point for agent tools."""
    source = CIViCSource()
    try:
        entries = await source.fetch_with_retry(gene_symbol, http)
        return {
            "source": "civic",
            "gene_symbol": gene_symbol,
            "entries": entries,
            "total": len(entries),
            "_sources": [f"https://civicdb.org/genes?name={gene_symbol}"],
        }
    except Exception as e:
        logger.warning("CIViC search failed for %s: %s", gene_symbol, e)
        return {"source": "civic", "gene_symbol": gene_symbol, "entries": [], "total": 0}


def run_civic(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: query CIViC for each gene."""
    import asyncio
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "civic"):
            continue
        if not gene.name:
            continue

        try:
            async_http = httpx.AsyncClient(timeout=20.0, follow_redirects=True)
            try:
                entries = asyncio.run(CIViCSource().fetch_with_retry(gene.name, async_http))
            finally:
                asyncio.run(async_http.aclose())

            if not entries:
                continue

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("civic"),
                payload={
                    "source": "CIViC",
                    "entries": entries,
                    "total": len(entries),
                },
                source_ref="civic",
                confidence=0.75,
            )
            count += 1
            logger.info("CIViC %s: %d entries", gene.name, len(entries))
        except Exception as e:
            logger.warning("CIViC %s error: %s", gene.name, e)

    return count
