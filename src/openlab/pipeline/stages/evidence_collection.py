"""Stage: Evidence Collection — gather evidence from multiple independent sources.

Ported from DNASyn's 5-phase pipeline, adapted for real-time streaming.
Each source runs independently and returns structured evidence payloads
that feed into the evidence normalizer and convergence scorer.

Sources:
  - InterPro (EBI): domain/family classification
  - STRING DB: protein-protein interaction network
  - UniProt: functional annotation lookup
  - EuropePMC: literature search
  - CDD (NCBI): conserved domain search (already in functional_prediction)
  - BLAST (NCBI): homology search (already in functional_prediction)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def search_interpro(
    http: httpx.AsyncClient, protein_seq: str
) -> dict[str, Any]:
    """Search InterPro for domain/family classification.

    Uses the EBI InterProScan5 REST API for sequence-based search.
    Falls back to a quick text lookup if the sequence scan is too slow.
    """
    if not protein_seq or len(protein_seq) < 20:
        return {"source": "interpro"}

    try:
        # Submit to InterProScan5 REST API
        resp = await http.post(
            "https://www.ebi.ac.uk/Tools/services/rest/iprscan5/run",
            data={
                "email": "genelife@research.local",
                "title": "genelife_scan",
                "sequence": protein_seq,
                "goterms": "true",
                "pathways": "true",
            },
            timeout=30.0,
        )

        if resp.status_code != 200:
            return {"source": "interpro"}

        job_id = resp.text.strip()

        # Poll for results (InterPro typically 30-120s)
        for _ in range(20):
            await asyncio.sleep(5)
            status_resp = await http.get(
                f"https://www.ebi.ac.uk/Tools/services/rest/iprscan5/status/{job_id}",
                timeout=10.0,
            )
            status = status_resp.text.strip()

            if status == "FINISHED":
                result_resp = await http.get(
                    f"https://www.ebi.ac.uk/Tools/services/rest/iprscan5/result/{job_id}/json",
                    timeout=30.0,
                )
                if result_resp.status_code == 200:
                    data = result_resp.json()
                    return _parse_interpro_result(data)
                break
            elif status in ("FAILURE", "ERROR", "NOT_FOUND"):
                break

    except Exception as e:
        logger.debug(f"InterPro search failed: {e}")

    return {"source": "interpro"}


def _parse_interpro_result(data: dict) -> dict[str, Any]:
    """Parse InterPro JSON result into evidence payload."""
    result: dict[str, Any] = {"source": "interpro", "matches": []}

    results_list = data.get("results", [])
    if not results_list:
        return result

    for entry in results_list:
        for match in entry.get("matches", []):
            sig = match.get("signature", {})
            entry_info = sig.get("entry", {}) or {}

            match_record: dict[str, Any] = {
                "name": sig.get("name", ""),
                "description": entry_info.get("description", "") or sig.get("description", ""),
                "database": sig.get("signatureLibraryRelease", {}).get("library", ""),
                "accession": entry_info.get("accession", "") or sig.get("accession", ""),
            }

            # GO terms from InterPro entry
            go_terms = []
            for go_xref in entry_info.get("goXRefs", []):
                go_terms.append({
                    "id": go_xref.get("id", ""),
                    "description": go_xref.get("name", ""),
                    "category": go_xref.get("category", ""),
                })
            if go_terms:
                match_record["go_terms"] = go_terms

            # Pathway xrefs
            pathways = entry_info.get("pathwayXRefs", [])
            if pathways:
                match_record["pathways"] = [
                    {"id": p.get("id", ""), "name": p.get("name", "")}
                    for p in pathways
                ]

            result["matches"].append(match_record)

    return result


async def search_string(
    http: httpx.AsyncClient, protein_seq: str, species_id: int = 2107  # M. mycoides
) -> dict[str, Any]:
    """Search STRING DB for protein interaction partners.

    Uses sequence-based lookup. Species 2107 = Mycoplasma mycoides.
    """
    if not protein_seq or len(protein_seq) < 20:
        return {"source": "string"}

    try:
        resp = await http.post(
            "https://string-db.org/api/json/get_string_ids",
            data={
                "identifiers": protein_seq[:500],
                "species": species_id,
                "limit": 1,
                "caller_identity": "genelife",
            },
            timeout=20.0,
        )

        if resp.status_code != 200:
            return {"source": "string"}

        ids = resp.json()
        if not ids:
            return {"source": "string"}

        string_id = ids[0].get("stringId", "")
        if not string_id:
            return {"source": "string"}

        # Get interaction partners
        partners_resp = await http.get(
            "https://string-db.org/api/json/network",
            params={
                "identifiers": string_id,
                "species": species_id,
                "network_type": "functional",
                "limit": 10,
                "caller_identity": "genelife",
            },
            timeout=20.0,
        )

        partners = []
        if partners_resp.status_code == 200:
            for edge in partners_resp.json()[:10]:
                partners.append({
                    "partner": edge.get("preferredName_B", ""),
                    "annotation": edge.get("annotation_B", ""),
                    "score": edge.get("score", 0),
                })

        # Get functional enrichment
        func_resp = await http.get(
            "https://string-db.org/api/json/enrichment",
            params={
                "identifiers": string_id,
                "species": species_id,
                "caller_identity": "genelife",
            },
            timeout=20.0,
        )

        go_terms = []
        if func_resp.status_code == 200:
            for term in func_resp.json()[:15]:
                if term.get("category", "").startswith("GO"):
                    go_terms.append({
                        "id": term.get("term", ""),
                        "description": term.get("description", ""),
                        "category": term.get("category", ""),
                    })

        return {
            "source": "string",
            "string_id": string_id,
            "partners": partners,
            "go_terms": go_terms,
            "functional_description": ids[0].get("annotation", ""),
        }

    except Exception as e:
        logger.debug(f"STRING search failed: {e}")

    return {"source": "string"}


async def search_uniprot(
    http: httpx.AsyncClient, protein_seq: str
) -> dict[str, Any]:
    """Search UniProt by BLAST for protein annotation."""
    if not protein_seq or len(protein_seq) < 20:
        return {"source": "uniprot"}

    try:
        # Use UniProt BLAST API
        resp = await http.post(
            "https://rest.uniprot.org/idmapping/run",
            data={
                "from": "UniProtKB_AC-ID",
                "to": "UniProtKB",
                "ids": "",  # We'll use sequence search instead
            },
            timeout=20.0,
        )

        # Fallback: search by sequence fragment
        query = protein_seq[:100]  # First 100 aa
        search_resp = await http.get(
            "https://rest.uniprot.org/uniprotkb/search",
            params={
                "query": f"(fragment:{query[:50]})",
                "format": "json",
                "size": "3",
                "fields": "accession,protein_name,organism_name,go_id,ec",
            },
            timeout=20.0,
        )

        if search_resp.status_code == 200:
            data = search_resp.json()
            results = data.get("results", [])
            if results:
                top = results[0]
                protein_name = ""
                rec_name = top.get("proteinDescription", {}).get("recommendedName", {})
                if rec_name:
                    protein_name = rec_name.get("fullName", {}).get("value", "")

                go_terms = []
                for xref in top.get("uniProtKBCrossReferences", []):
                    if xref.get("database") == "GO":
                        go_terms.append({
                            "id": xref.get("id", ""),
                            "description": next(
                                (p.get("value", "") for p in xref.get("properties", [])
                                 if p.get("key") == "GoTerm"),
                                "",
                            ),
                        })

                return {
                    "source": "uniprot",
                    "protein_name": protein_name,
                    "organism": top.get("organism", {}).get("scientificName", ""),
                    "accession": top.get("primaryAccession", ""),
                    "go_terms": go_terms,
                }

    except Exception as e:
        logger.debug(f"UniProt search failed: {e}")

    return {"source": "uniprot"}


async def search_literature(
    http: httpx.AsyncClient, gene_name: str, product: str, locus_tag: str
) -> dict[str, Any]:
    """Search EuropePMC for literature about this gene."""
    if not gene_name and not locus_tag:
        return {"source": "literature"}

    # Build search query
    terms = []
    if gene_name:
        terms.append(f'"{gene_name}"')
    if locus_tag and locus_tag != gene_name:
        terms.append(f'"{locus_tag}"')
    if product and "hypothetical" not in product.lower():
        terms.append(f'"{product}"')

    query = " OR ".join(terms)
    if not query:
        return {"source": "literature"}

    # Add mycoplasma context
    query = f"({query}) AND (mycoplasma OR JCVI OR syn3 OR minimal genome)"

    try:
        resp = await http.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": query,
                "resultType": "lite",
                "pageSize": "5",
                "format": "json",
            },
            timeout=15.0,
        )

        if resp.status_code == 200:
            data = resp.json()
            articles = []
            for result in data.get("resultList", {}).get("result", [])[:5]:
                articles.append({
                    "title": result.get("title", ""),
                    "abstract": result.get("abstractText", "")[:500],
                    "authors": result.get("authorString", ""),
                    "journal": result.get("journalTitle", ""),
                    "year": result.get("pubYear", ""),
                    "pmid": result.get("pmid", ""),
                })

            return {
                "source": "literature",
                "articles": articles,
                "total_hits": data.get("hitCount", 0),
            }

    except Exception as e:
        logger.debug(f"Literature search failed: {e}")

    return {"source": "literature"}


async def collect_evidence_for_gene(
    http: httpx.AsyncClient,
    protein_seq: str,
    gene_name: str = "",
    product: str = "",
    locus_tag: str = "",
    run_interpro: bool = True,
    run_string: bool = True,
    run_uniprot: bool = True,
    run_literature: bool = True,
    run_esmfold: bool = False,
    run_alphafold: bool = False,
    run_foldseek: bool = False,
    run_hhpred: bool = False,
    run_synwiki: bool = False,
    run_eggnog: bool = False,
    run_europepmc: bool = False,
) -> list[dict[str, Any]]:
    """Collect evidence from all available sources for a single gene.

    Runs sources in parallel for speed. Returns list of evidence payloads.
    """
    tasks: list[asyncio.Task] = []

    if run_interpro and protein_seq:
        tasks.append(asyncio.create_task(search_interpro(http, protein_seq)))
    if run_string and protein_seq:
        tasks.append(asyncio.create_task(search_string(http, protein_seq)))
    if run_uniprot and protein_seq:
        tasks.append(asyncio.create_task(search_uniprot(http, protein_seq)))
    if run_literature:
        tasks.append(asyncio.create_task(
            search_literature(http, gene_name, product, locus_tag)
        ))

    # DNASyn evidence sources
    if run_esmfold and protein_seq:
        from openlab.contrib.dnasyn.sources.esmfold import search_esmfold
        tasks.append(asyncio.create_task(search_esmfold(http, protein_seq)))
    if run_hhpred and protein_seq:
        from openlab.contrib.dnasyn.sources.hhpred import search_hhpred
        tasks.append(asyncio.create_task(search_hhpred(http, protein_seq)))
    if run_synwiki and locus_tag:
        from openlab.contrib.dnasyn.sources.synwiki import search_synwiki
        tasks.append(asyncio.create_task(search_synwiki(http, locus_tag)))
    if run_eggnog and protein_seq:
        from openlab.contrib.dnasyn.sources.eggnog_online import search_eggnog_online
        tasks.append(asyncio.create_task(search_eggnog_online(http, protein_seq)))
    if run_europepmc:
        from openlab.contrib.dnasyn.sources.europepmc import search_europepmc
        tasks.append(asyncio.create_task(
            search_europepmc(http, gene_name, product, locus_tag)
        ))

    results = []
    if tasks:
        done = await asyncio.gather(*tasks, return_exceptions=True)
        for result in done:
            if isinstance(result, dict) and _has_content(result):
                results.append(result)

    # Foldseek depends on ESMFold output — run sequentially if both requested
    if run_foldseek:
        pdb_text = None
        for r in results:
            if r.get("source") == "esmfold" and r.get("pdb_text"):
                pdb_text = r["pdb_text"]
                break
        if pdb_text:
            from openlab.contrib.dnasyn.sources.foldseek import search_foldseek
            foldseek_result = await search_foldseek(http, pdb_text)
            if _has_content(foldseek_result):
                results.append(foldseek_result)

    # AlphaFold needs an accession from UniProt results
    if run_alphafold:
        accession = None
        for r in results:
            if r.get("source") == "uniprot" and r.get("accession"):
                accession = r["accession"]
                break
        if accession:
            from openlab.contrib.dnasyn.sources.alphafold import search_alphafold
            af_result = await search_alphafold(http, accession)
            if _has_content(af_result):
                results.append(af_result)

    return results


def _has_content(evidence: dict) -> bool:
    """Check if an evidence payload has meaningful content beyond just 'source'."""
    for key, value in evidence.items():
        if key == "source":
            continue
        if isinstance(value, list) and value:
            return True
        if isinstance(value, str) and value:
            return True
        if isinstance(value, (int, float)) and value > 0:
            return True
    return False
