"""NCBI genome search and download via Entrez."""

from Bio import Entrez

from openlab.config import config


def _setup_entrez():
    """Configure Entrez credentials from app config."""
    Entrez.email = config.ncbi.email
    if config.ncbi.api_key:
        Entrez.api_key = config.ncbi.api_key


def search_genomes(query: str, max_results: int = 20) -> list[dict]:
    """Search NCBI nucleotide DB for complete bacterial genomes."""
    _setup_entrez()

    term = f'({query}) AND "complete genome"[Title] AND 1:2000000[SLEN] AND bacteria[Filter]'

    handle = Entrez.esearch(
        db="nucleotide", term=term, retmax=max_results, idtype="acc"
    )
    search_results = Entrez.read(handle)
    handle.close()

    id_list = search_results.get("IdList", [])
    if not id_list:
        return []

    handle = Entrez.esummary(db="nucleotide", id=",".join(id_list))
    summaries = Entrez.read(handle)
    handle.close()

    results = []
    for doc in summaries:
        results.append({
            "accession": doc.get("AccessionVersion", doc.get("Caption", "")),
            "organism": doc.get("Title", "").split(",")[0],
            "title": doc.get("Title", ""),
            "length": int(doc.get("Length", 0)),
        })

    return results


def fetch_genbank(accession: str) -> str:
    """Download a GenBank record by accession."""
    _setup_entrez()

    handle = Entrez.efetch(
        db="nucleotide", id=accession, rettype="gb", retmode="text"
    )
    text = handle.read()
    handle.close()

    return text
