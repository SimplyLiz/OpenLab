"""Tests for COSMIC cancer evidence source."""

import httpx
import pytest
import respx

from openlab.contrib.cancer.sources.cosmic import CosmicSource, search_cosmic


@pytest.mark.asyncio
async def test_cosmic_fetch(cosmic_response):
    """COSMIC fetch returns normalized mutations."""
    async with respx.mock:
        respx.get("https://clinicaltables.nlm.nih.gov/api/cosmic/v4/search").respond(
            json=cosmic_response,
        )

        async with httpx.AsyncClient() as http:
            source = CosmicSource()
            results = await source.fetch("BRAF", http)

    assert len(results) == 3
    assert results[0]["source"] == "cosmic"
    assert results[0]["gene_symbol"] == "BRAF"
    assert results[0]["aa_mutation"] == "p.V600E"
    assert "cancer:somatic_mutation" in results[0]["categories"]


@pytest.mark.asyncio
async def test_cosmic_normalize():
    """COSMIC normalize categorizes mutation types."""
    source = CosmicSource()
    raw = {
        "code": "COSM476",
        "display": ["COSM476", "BRAF", "c.1799T>A", "p.V600E", "skin", "melanoma"],
        "gene_symbol": "BRAF",
        "total_in_db": 100,
    }
    result = source.normalize(raw)
    assert result["cds_mutation"] == "c.1799T>A"
    assert result["primary_site"] == "skin"
    assert result["histology"] == "melanoma"


@pytest.mark.asyncio
async def test_cosmic_empty_response():
    """COSMIC handles empty search results."""
    async with respx.mock:
        respx.get("https://clinicaltables.nlm.nih.gov/api/cosmic/v4/search").respond(
            json=[0, [], None, []],
        )

        async with httpx.AsyncClient() as http:
            source = CosmicSource()
            results = await source.fetch("NONEXISTENT", http)

    assert results == []


@pytest.mark.asyncio
async def test_search_cosmic_wrapper(cosmic_response):
    """search_cosmic wraps CosmicSource."""
    async with respx.mock:
        respx.get("https://clinicaltables.nlm.nih.gov/api/cosmic/v4/search").respond(
            json=cosmic_response,
        )

        async with httpx.AsyncClient() as http:
            result = await search_cosmic(http, "BRAF")

    assert result["source"] == "cosmic"
    assert result["total"] == 3
