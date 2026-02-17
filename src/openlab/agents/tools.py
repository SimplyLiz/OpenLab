"""Tool registry — wraps existing services with provenance tracking."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from openlab.agents.agent_models import ToolResult
from openlab.agents.provenance import ProvenanceLedger

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of callable tools with automatic provenance tracking."""

    def __init__(self, http: httpx.AsyncClient, ledger: ProvenanceLedger) -> None:
        self.http = http
        self.ledger = ledger
        self._tools: dict[str, Any] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        self._tools["ncbi_gene_info"] = _ncbi_gene_info
        self._tools["ensembl_lookup"] = _ensembl_lookup
        self._tools["uniprot_lookup"] = _uniprot_lookup
        self._tools["literature_search"] = _literature_search
        self._tools["cancer_literature"] = _cancer_literature
        self._tools["pmid_validate"] = _pmid_validate
        self._tools["evidence_fetch"] = _evidence_fetch
        self._tools["convergence_score"] = _convergence_score
        self._tools["llm_synthesize"] = _llm_synthesize

    async def call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        parent_call_id: str | None = None,
    ) -> ToolResult:
        func = self._tools.get(tool_name)
        if func is None:
            return ToolResult(
                call_id="",
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}",
            )

        call_id = await self.ledger.start_call(tool_name, arguments, parent_call_id)
        try:
            result = await func(self.http, **arguments)
            sources = result.pop("_sources", []) if isinstance(result, dict) else []
            await self.ledger.complete_call(call_id, sources=sources, success=True)
            return ToolResult(
                call_id=call_id,
                tool_name=tool_name,
                success=True,
                data=result if isinstance(result, dict) else {"result": result},
                sources=sources,
            )
        except Exception as exc:
            logger.warning("Tool %s failed: %s", tool_name, exc)
            await self.ledger.complete_call(call_id, success=False, error=str(exc))
            return ToolResult(
                call_id=call_id,
                tool_name=tool_name,
                success=False,
                error=str(exc),
            )

    @property
    def available_tools(self) -> list[str]:
        return list(self._tools)


# ---------------------------------------------------------------------------
# Built-in tool implementations
# ---------------------------------------------------------------------------


async def _ncbi_gene_info(http: httpx.AsyncClient, gene_symbol: str, **kw) -> dict[str, Any]:
    from openlab.services.ncbi import get_gene_info, search_gene

    gene_id = await search_gene(http, gene_symbol)
    if not gene_id:
        return {"gene_id": None, "error": f"Gene {gene_symbol} not found in NCBI"}
    info: dict[str, Any] = await get_gene_info(http, gene_id)
    info["_sources"] = [f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}"]
    return info


async def _ensembl_lookup(http: httpx.AsyncClient, gene_symbol: str, **kw) -> dict[str, Any]:
    from openlab.services.ensembl import lookup_symbol

    data = await lookup_symbol(http, gene_symbol, species="homo_sapiens")
    if data:
        data["_sources"] = [f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{gene_symbol}"]
    return data or {"error": f"Ensembl lookup failed for {gene_symbol}"}


async def _uniprot_lookup(http: httpx.AsyncClient, gene_symbol: str, **kw) -> dict[str, Any]:
    from openlab.services.uniprot import search_by_gene

    data = await search_by_gene(http, gene_symbol)
    if data:
        data["_sources"] = [f"https://rest.uniprot.org/uniprotkb/search?query={gene_symbol}"]
    return data or {"error": f"UniProt lookup failed for {gene_symbol}"}


async def _literature_search(http: httpx.AsyncClient, gene_symbol: str, **kw) -> dict[str, Any]:
    from openlab.contrib.dnasyn.sources.europepmc import search_europepmc

    articles = await search_europepmc(http, gene_symbol, product=kw.get("product", ""))
    return {
        "articles": articles if isinstance(articles, list) else [articles] if articles else [],
        "_sources": ["https://europepmc.org"],
    }


async def _cancer_literature(
    http: httpx.AsyncClient, gene_symbol: str, cancer_type: str = "", **kw
) -> dict[str, Any]:
    query = f'"{gene_symbol}" AND ("cancer" OR "oncogene" OR "tumor suppressor")'
    if cancer_type:
        query += f' AND "{cancer_type}"'
    resp = await http.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={
            "query": query,
            "format": "json",
            "pageSize": "25",
            "sort": "CITED desc",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("resultList", {}).get("result", [])
    articles = [
        {
            "pmid": r.get("pmid", ""),
            "title": r.get("title", ""),
            "authors": r.get("authorString", ""),
            "journal": r.get("journalTitle", ""),
            "year": r.get("pubYear", ""),
            "doi": r.get("doi", ""),
            "cited_by": r.get("citedByCount", 0),
        }
        for r in results
    ]
    return {"articles": articles, "_sources": ["https://europepmc.org"]}


async def _pmid_validate(http: httpx.AsyncClient, pmid: str, **kw) -> dict[str, Any]:
    resp = await http.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={"query": f"EXT_ID:{pmid}", "format": "json", "pageSize": "1"},
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("resultList", {}).get("result", [])
    valid = len(results) > 0
    return {
        "pmid": pmid,
        "valid": valid,
        "title": results[0].get("title", "") if valid else "",
        "_sources": [f"https://europepmc.org/article/MED/{pmid}"] if valid else [],
    }


async def _evidence_fetch(
    http: httpx.AsyncClient, gene_id: int | None = None, **kw: Any,
) -> dict[str, Any]:
    if gene_id is None:
        return {"evidence": [], "_sources": []}
    from openlab.db import get_session_factory
    from openlab.services.evidence_service import list_evidence

    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        evidence = list_evidence(db, gene_id=gene_id)
        return {
            "evidence": [
                {
                    "evidence_type": str(e.evidence_type.value),
                    "payload": e.payload,
                    "source_ref": e.source_ref,
                    "confidence": e.confidence,
                }
                for e in evidence
            ],
            "_sources": ["local_database"],
        }


async def _convergence_score(http: httpx.AsyncClient, evidence_list: list, **kw) -> dict[str, Any]:
    from openlab.services.convergence import compute_convergence

    score = compute_convergence(evidence_list)
    return {"convergence_score": score, "_sources": ["convergence_algorithm"]}


async def _llm_synthesize(
    http: httpx.AsyncClient, prompt: str, system_prompt: str | None = None, **kw
) -> dict[str, Any]:
    from openlab.services.llm_synthesis import synthesize

    response = await synthesize(http, prompt, purpose="cancer_dossier")
    return {"response": response, "_sources": ["llm_synthesis"]}
