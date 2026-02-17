"""NCBI E-utilities adapter.

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/
Rate limit: 3 req/s without API key, 10 req/s with.
"""

from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from openlab.config import config

_BASE = config.ncbi.base_url
_THROTTLE = 1.0 / config.ncbi.requests_per_second
_last_request = 0.0


async def _throttle():
    global _last_request
    now = time.monotonic()
    wait = _THROTTLE - (now - _last_request)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request = time.monotonic()


def _params(**kwargs) -> dict:
    """Build query params, injecting API key if configured."""
    p = {k: v for k, v in kwargs.items() if v}
    if config.ncbi.api_key:
        p["api_key"] = config.ncbi.api_key
    return p


# ---------------------------------------------------------------------------
# Gene search & info
# ---------------------------------------------------------------------------

async def search_gene(http: httpx.AsyncClient, query: str) -> str | None:
    """Search for a gene by symbol/name and return the NCBI Gene ID."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/esearch.fcgi",
        params=_params(db="gene", term=f"{query}[Gene Name] AND Homo sapiens[Organism]",
                       retmode="json", retmax="5"),
    )
    resp.raise_for_status()
    data = resp.json()
    id_list = data.get("esearchresult", {}).get("idlist", [])
    return id_list[0] if id_list else None


async def get_gene_info(http: httpx.AsyncClient, gene_id: str) -> dict[str, Any]:
    """Fetch full gene record from NCBI Gene database.

    Returns a dict with keys: symbol, name, summary, aliases, chromosome,
    map_location, refseq_mrna, refseq_protein, organism, mim_ids.
    """
    await _throttle()
    resp = await http.get(
        f"{_BASE}/efetch.fcgi",
        params=_params(db="gene", id=gene_id, rettype="xml", retmode="xml"),
    )
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    gene_el = root.find(".//Entrezgene")
    if gene_el is None:
        return {}

    info: dict[str, Any] = {"ncbi_gene_id": gene_id}

    # Gene-ref block
    gene_ref = gene_el.find(".//Gene-ref")
    if gene_ref is not None:
        locus = gene_ref.findtext("Gene-ref_locus", "")
        desc = gene_ref.findtext("Gene-ref_desc", "")
        info["symbol"] = locus
        info["name"] = desc

        # Aliases
        syn_el = gene_ref.find("Gene-ref_syn")
        if syn_el is not None:
            info["aliases"] = [s.text for s in syn_el.findall("Gene-ref_syn_E") if s.text]

    # Summary
    for comment in gene_el.findall(".//Entrezgene_summary"):
        if comment.text:
            info["summary"] = comment.text
            break

    # Chromosome / map location
    source = gene_el.find(".//Gene-source")
    if source is not None:
        info["organism"] = source.findtext("Gene-source_src-str1", "Homo sapiens")

    maps = gene_el.find(".//Maps")
    if maps is not None:
        display = maps.findtext(".//Maps_display-str", "")
        info["map_location"] = display

    # Gene-commentary for RefSeq transcripts
    # Accessions appear under Gene-commentary elements with heading "Reference"
    mrnas = []
    proteins = []
    for gc in gene_el.iter("Gene-commentary"):
        acc = gc.findtext("Gene-commentary_accession", "")
        if acc.startswith("NM_"):
            mrnas.append(acc)
        elif acc.startswith("NP_"):
            proteins.append(acc)

    # Prefer the canonical transcript — typically the one with the lowest accession number
    # (e.g. NM_000546 for TP53, not NM_001276761)
    if mrnas:
        mrnas_unique = sorted(set(mrnas))
        info["refseq_mrna"] = mrnas_unique[0]
    if proteins:
        proteins_unique = sorted(set(proteins))
        info["refseq_protein"] = proteins_unique[0]

    return info


# ---------------------------------------------------------------------------
# Sequence fetch
# ---------------------------------------------------------------------------

async def fetch_sequence(
    http: httpx.AsyncClient, accession: str, db: str = "nucleotide", rettype: str = "fasta"
) -> str:
    """Fetch a sequence by accession in FASTA format."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/efetch.fcgi",
        params=_params(db=db, id=accession, rettype=rettype, retmode="text"),
    )
    resp.raise_for_status()
    return resp.text


async def fetch_protein_sequence(http: httpx.AsyncClient, accession: str) -> str:
    """Fetch protein sequence by RefSeq protein accession."""
    return await fetch_sequence(http, accession, db="protein", rettype="fasta")


# ---------------------------------------------------------------------------
# PubMed count
# ---------------------------------------------------------------------------

async def get_pubmed_count(http: httpx.AsyncClient, gene_symbol: str) -> int:
    """Get approximate number of PubMed articles mentioning this gene."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/esearch.fcgi",
        params=_params(db="pubmed", term=f"{gene_symbol}[Title/Abstract]",
                       rettype="count", retmode="json"),
    )
    resp.raise_for_status()
    data = resp.json()
    return int(data.get("esearchresult", {}).get("count", 0))


# ---------------------------------------------------------------------------
# Linked records (for cross-references)
# ---------------------------------------------------------------------------

async def get_gene_links(
    http: httpx.AsyncClient, gene_id: str, target_db: str
) -> list[str]:
    """Get linked IDs from Gene to another NCBI database (e.g. 'omim', 'clinvar')."""
    await _throttle()
    resp = await http.get(
        f"{_BASE}/elink.fcgi",
        params=_params(dbfrom="gene", db=target_db, id=gene_id, retmode="json"),
    )
    resp.raise_for_status()
    data = resp.json()
    link_sets = data.get("linksets", [])
    ids = []
    for ls in link_sets:
        for ldb in ls.get("linksetdbs", []):
            ids.extend(str(x) for x in ldb.get("links", []))
    return ids
