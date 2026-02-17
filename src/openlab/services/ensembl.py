"""Ensembl REST API adapter.

Docs: https://rest.ensembl.org
Rate limit: 15 req/s, 55k req/hour.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from openlab.config import config

_BASE = config.ensembl.base_url
_THROTTLE = 1.0 / config.ensembl.requests_per_second
_last_request = 0.0
_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


async def _throttle():
    global _last_request
    now = time.monotonic()
    wait = _THROTTLE - (now - _last_request)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request = time.monotonic()


# ---------------------------------------------------------------------------
# Gene lookup by symbol
# ---------------------------------------------------------------------------

async def lookup_symbol(
    http: httpx.AsyncClient, symbol: str, species: str = "homo_sapiens"
) -> dict[str, Any] | None:
    """Look up a gene by symbol. Returns Ensembl gene record or None."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/lookup/symbol/{species}/{symbol}",
        headers=_HEADERS,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Gene info by Ensembl ID
# ---------------------------------------------------------------------------

async def get_gene(http: httpx.AsyncClient, ensembl_id: str) -> dict[str, Any] | None:
    """Get gene info by Ensembl gene ID."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/lookup/id/{ensembl_id}",
        headers=_HEADERS,
        params={"expand": "1"},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Cross-references (xrefs)
# ---------------------------------------------------------------------------

async def get_xrefs(
    http: httpx.AsyncClient, ensembl_id: str, external_db: str | None = None
) -> list[dict[str, Any]]:
    """Get cross-references for an Ensembl ID.

    Optional filter by external_db (e.g. 'UniProt/SWISSPROT', 'HGNC', 'RefSeq_mRNA').
    """
    await _throttle()
    params = {}
    if external_db:
        params["external_db"] = external_db
    resp = await http.get(
        f"{_BASE}/xrefs/id/{ensembl_id}",
        headers=_HEADERS,
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Sequence
# ---------------------------------------------------------------------------

async def get_sequence(
    http: httpx.AsyncClient,
    ensembl_id: str,
    seq_type: str = "genomic",  # "genomic", "cdna", "cds", "protein"
) -> str:
    """Get sequence for an Ensembl ID."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/sequence/id/{ensembl_id}",
        headers={"Accept": "text/plain"},
        params={"type": seq_type},
    )
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# Homology
# ---------------------------------------------------------------------------

async def get_homologs(
    http: httpx.AsyncClient, ensembl_id: str, homology_type: str = "orthologues"
) -> list[dict[str, Any]]:
    """Get orthologs/paralogs for a gene."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/homology/id/{ensembl_id}",
        headers=_HEADERS,
        params={"type": homology_type, "format": "condensed"},
    )
    resp.raise_for_status()
    data = resp.json()
    homologies = data.get("data", [{}])[0].get("homologies", [])
    return homologies


# ---------------------------------------------------------------------------
# Functional annotation (GO terms)
# ---------------------------------------------------------------------------

async def get_go_terms(
    http: httpx.AsyncClient, ensembl_id: str
) -> list[dict[str, str]]:
    """Get GO term annotations via xrefs filtered to GO database."""
    xrefs = await get_xrefs(http, ensembl_id, external_db="GO")
    terms = []
    for x in xrefs:
        display = x.get("display_id", "")
        desc = x.get("description", "")
        linkage = x.get("linkage_types", [{}])
        evidence = linkage[0].get("evidence", "") if linkage else ""
        if display.startswith("GO:"):
            terms.append({
                "go_id": display,
                "name": desc,
                "evidence": evidence,
            })
    return terms
