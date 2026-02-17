"""Evidence retriever — fetches gene identity and literature via ToolRegistry."""

from __future__ import annotations

from typing import Any

from openlab.agents.tools import ToolRegistry


async def retrieve_gene_identity(
    tools: ToolRegistry, gene_symbol: str
) -> tuple[dict[str, Any], list[str]]:
    """Fetch gene identity from NCBI, Ensembl, UniProt in parallel."""
    import asyncio

    results = await asyncio.gather(
        tools.call("ncbi_gene_info", {"gene_symbol": gene_symbol}),
        tools.call("ensembl_lookup", {"gene_symbol": gene_symbol}),
        tools.call("uniprot_lookup", {"gene_symbol": gene_symbol}),
        return_exceptions=True,
    )

    identity: dict[str, Any] = {"gene_symbol": gene_symbol}
    call_ids: list[str] = []

    for r in results:
        if isinstance(r, BaseException):
            continue
        if r.success:
            identity.update(r.data)
            call_ids.append(r.call_id)

    return identity, call_ids


async def retrieve_literature(
    tools: ToolRegistry, gene_symbol: str, cancer_type: str | None = None
) -> tuple[list[dict], list[str]]:
    """Fetch literature from EuropePMC (general + cancer-specific)."""
    import asyncio

    tasks = [tools.call("literature_search", {"gene_symbol": gene_symbol})]
    if cancer_type:
        tasks.append(tools.call(
            "cancer_literature",
            {"gene_symbol": gene_symbol, "cancer_type": cancer_type},
        ))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    articles: list[dict] = []
    call_ids: list[str] = []

    for r in results:
        if isinstance(r, BaseException):
            continue
        if r.success:
            articles.extend(r.data.get("articles", []))
            call_ids.append(r.call_id)

    return articles, call_ids


async def retrieve_existing_evidence(
    tools: ToolRegistry, gene_symbol: str, gene_id: int | None = None
) -> tuple[list[dict], list[str]]:
    """Fetch existing evidence from the local database."""
    result = await tools.call("evidence_fetch", {"gene_id": gene_id})
    call_ids = [result.call_id] if result.success else []
    evidence = result.data.get("evidence", []) if result.success else []
    return evidence, call_ids
