"""UniProt REST API adapter.

Docs: https://www.uniprot.org/help/api
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from openlab.config import config

_BASE = config.uniprot.base_url
_THROTTLE = 1.0 / config.uniprot.requests_per_second
_last_request = 0.0


async def _throttle():
    global _last_request
    now = time.monotonic()
    wait = _THROTTLE - (now - _last_request)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request = time.monotonic()


async def search_by_gene(
    http: httpx.AsyncClient, gene_symbol: str, organism: str = "9606"
) -> dict[str, Any] | None:
    """Search UniProt for a gene symbol in a given organism (default: human).

    Returns the top reviewed (Swiss-Prot) entry or None.
    """
    await _throttle()
    query = f"(gene:{gene_symbol}) AND (organism_id:{organism}) AND (reviewed:true)"
    resp = await http.get(
        f"{_BASE}/uniprotkb/search",
        params={"query": query, "format": "json", "size": "1", "fields": "accession"},
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return None
    accession = results[0].get("primaryAccession", "")
    return await get_entry(http, accession)


async def get_entry(http: httpx.AsyncClient, accession: str) -> dict[str, Any]:
    """Get a full UniProt entry by accession."""
    await _throttle()
    resp = await http.get(f"{_BASE}/uniprotkb/{accession}.json")
    resp.raise_for_status()
    return resp.json()


def extract_go_terms(entry: dict) -> list[dict[str, str]]:
    """Extract GO terms from a UniProt JSON entry."""
    terms = []
    for ref in entry.get("uniProtKBCrossReferences", []):
        if ref.get("database") == "GO":
            go_id = ref.get("id", "")
            props = {p["key"]: p["value"] for p in ref.get("properties", [])}
            name = props.get("GoTerm", "")
            evidence = props.get("GoEvidenceType", "")
            # Parse category from GoTerm prefix (C:, F:, P:)
            category = ""
            if name.startswith("C:"):
                category = "cellular_component"
                name = name[2:]
            elif name.startswith("F:"):
                category = "molecular_function"
                name = name[2:]
            elif name.startswith("P:"):
                category = "biological_process"
                name = name[2:]
            terms.append({
                "go_id": go_id, "name": name,
                "category": category, "evidence": evidence,
            })
    return terms


def extract_diseases(entry: dict) -> list[dict[str, str]]:
    """Extract disease associations from UniProt entry."""
    diseases = []
    for comment in entry.get("comments", []):
        if comment.get("commentType") == "DISEASE":
            disease = comment.get("disease", {})
            name = disease.get("diseaseId", "")
            mim_ref = disease.get("diseaseCrossReference", {})
            mim_id = mim_ref.get("id", "")
            if name:
                diseases.append({
                    "disease": name, "source": "UniProt",
                    "mim_id": mim_id,
                })
    return diseases


def extract_function_summary(entry: dict) -> str:
    """Extract function description from UniProt entry."""
    for comment in entry.get("comments", []):
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts", [])
            if texts:
                return texts[0].get("value", "")
    return ""


def extract_pathways(entry: dict) -> list[dict[str, str]]:
    """Extract pathway cross-references (Reactome, KEGG)."""
    pathways = []
    for ref in entry.get("uniProtKBCrossReferences", []):
        db = ref.get("database", "")
        if db in ("Reactome", "KEGG"):
            pathway_id = ref.get("id", "")
            props = {p["key"]: p["value"] for p in ref.get("properties", [])}
            name = props.get("PathwayName", pathway_id)
            pathways.append({
                "pathway_id": pathway_id,
                "name": name,
                "source": db,
            })
    return pathways
