"""Evidence retriever — fetches gene identity and literature via ToolRegistry."""

from __future__ import annotations

from typing import Any

from openlab.agents.tools import ToolRegistry


async def retrieve_gene_identity(
    tools: ToolRegistry, gene_symbol: str
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    """Fetch gene identity from NCBI, Ensembl, UniProt in parallel.

    Returns (merged_identity, call_ids, per_source_data) where per_source_data
    is a list of individual source results tagged with their source name.
    """
    import asyncio

    source_names = ["ncbi", "ensembl", "uniprot"]
    results = await asyncio.gather(
        tools.call("ncbi_gene_info", {"gene_symbol": gene_symbol}),
        tools.call("ensembl_lookup", {"gene_symbol": gene_symbol}),
        tools.call("uniprot_lookup", {"gene_symbol": gene_symbol}),
        return_exceptions=True,
    )

    identity: dict[str, Any] = {"gene_symbol": gene_symbol}
    call_ids: list[str] = []
    per_source: list[dict[str, Any]] = []

    for name, r in zip(source_names, results, strict=True):
        if isinstance(r, BaseException):
            continue
        if r.success:
            identity.update(r.data)
            call_ids.append(r.call_id)
            per_source.append({"source": name, **r.data})

    return identity, call_ids, per_source


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


async def retrieve_cancer_evidence(
    tools: ToolRegistry, gene_symbol: str
) -> tuple[list[dict], list[str]]:
    """Fetch cancer evidence from all 6 sources in parallel.

    Returns (cancer_evidence_list, call_ids) where each item in the list is
    an individual evidence dict (variant/mutation/entry) tagged with its source.
    """
    import asyncio

    source_tools = [
        "clinvar_search",
        "cosmic_search",
        "oncokb_search",
        "cbioportal_search",
        "civic_search",
        "tcga_gdc_search",
    ]

    results = await asyncio.gather(
        *(tools.call(t, {"gene_symbol": gene_symbol}) for t in source_tools),
        return_exceptions=True,
    )

    evidence: list[dict] = []
    call_ids: list[str] = []

    for r in results:
        if isinstance(r, BaseException):
            continue
        if not r.success:
            continue
        call_ids.append(r.call_id)
        source = r.data.get("source", "unknown")
        # Flatten inner items from variants/mutations/entries into individual evidence
        for key in ("variants", "mutations", "entries"):
            items = r.data.get(key, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    item.setdefault("source", source)
                    evidence.append(item)
        # If no inner items, include the top-level result as evidence
        if not any(r.data.get(k) for k in ("variants", "mutations", "entries")):
            evidence.append({"source": source, **r.data})

    return evidence, call_ids


async def retrieve_existing_evidence(
    tools: ToolRegistry, gene_symbol: str, gene_id: int | None = None
) -> tuple[list[dict], list[str]]:
    """Fetch existing evidence from the local database."""
    result = await tools.call("evidence_fetch", {"gene_id": gene_id})
    call_ids = [result.call_id] if result.success else []
    evidence = result.data.get("evidence", []) if result.success else []
    return evidence, call_ids
