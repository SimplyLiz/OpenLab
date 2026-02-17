"""Tests for OncoKB cancer evidence source."""

import httpx
import pytest
import respx

from openlab.contrib.cancer.sources.oncokb import OncoKBSource, search_oncokb


@pytest.mark.asyncio
async def test_oncokb_fetch(oncokb_response):
    """OncoKB fetch returns gene + variant entries."""
    async with respx.mock:
        respx.get("https://www.oncokb.org/api/v1/genes/lookup").respond(
            json=oncokb_response["gene_lookup"],
        )
        respx.get("https://www.oncokb.org/api/v1/variants/lookup").respond(
            json=oncokb_response["variants_lookup"],
        )

        async with httpx.AsyncClient() as http:
            source = OncoKBSource()
            results = await source.fetch("BRAF", http)

    # 1 gene + 2 variants
    assert len(results) == 3
    gene_results = [r for r in results if r.get("record_type") == "gene"]
    variant_results = [r for r in results if r.get("record_type") == "variant"]
    assert len(gene_results) == 1
    assert len(variant_results) == 2

    # Gene-level checks
    assert gene_results[0]["oncogene"] is True
    assert "cancer:oncogene" in gene_results[0]["categories"]

    # Variant-level checks
    assert variant_results[0]["variant_name"] == "V600E"
    assert "mutation:gain_of_function" in variant_results[0]["categories"]
    assert "cancer:oncogenic" in variant_results[0]["categories"]


@pytest.mark.asyncio
async def test_oncokb_normalize_tsg():
    """OncoKB normalizes tumor suppressors correctly."""
    source = OncoKBSource()
    gene_data = {
        "hugoSymbol": "TP53",
        "entrezGeneId": 7157,
        "oncogene": False,
        "tsg": True,
    }
    result = source._normalize_gene(gene_data)
    assert "cancer:tumor_suppressor" in result["categories"]
    assert "cancer:oncogene" not in result["categories"]


@pytest.mark.asyncio
async def test_oncokb_empty_gene():
    """OncoKB returns empty list for unknown gene."""
    async with respx.mock:
        respx.get("https://www.oncokb.org/api/v1/genes/lookup").respond(json=[])
        respx.get("https://www.oncokb.org/api/v1/variants/lookup").respond(json=[])

        async with httpx.AsyncClient() as http:
            source = OncoKBSource()
            results = await source.fetch("FAKE_GENE", http)

    assert results == []


@pytest.mark.asyncio
async def test_search_oncokb_error_handling():
    """search_oncokb handles API errors gracefully."""
    async with respx.mock:
        respx.get("https://www.oncokb.org/api/v1/genes/lookup").respond(status_code=500)

        async with httpx.AsyncClient() as http:
            result = await search_oncokb(http, "BRAF")

    assert result["source"] == "oncokb"
    assert result["entries"] == []
    assert result["total"] == 0
