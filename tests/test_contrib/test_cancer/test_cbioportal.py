"""Tests for cBioPortal cancer evidence source."""

import httpx
import pytest
import respx

from openlab.contrib.cancer.sources.cbioportal import CBioPortalSource, search_cbioportal


@pytest.mark.asyncio
async def test_cbioportal_fetch(cbioportal_response):
    """cBioPortal fetch returns normalized mutations."""
    async with respx.mock:
        respx.get("https://www.cbioportal.org/api/genes/TP53").respond(
            json=cbioportal_response["gene"],
        )
        respx.get("https://www.cbioportal.org/api/mutations").respond(
            json=cbioportal_response["mutations"],
        )

        async with httpx.AsyncClient() as http:
            source = CBioPortalSource()
            results = await source.fetch("TP53", http)

    assert len(results) == 2
    assert results[0]["source"] == "cbioportal"
    assert results[0]["protein_change"] == "R175H"
    assert "mutation:missense" in results[0]["categories"]
    assert "mutation:loss_of_function" in results[1]["categories"]


@pytest.mark.asyncio
async def test_cbioportal_normalize_mutation_types():
    """cBioPortal normalizes various mutation types."""
    source = CBioPortalSource()

    cases = [
        ("Missense_Mutation", "mutation:missense"),
        ("Nonsense_Mutation", "mutation:loss_of_function"),
        ("Frame_Shift_Del", "mutation:loss_of_function"),
        ("Splice_Site", "mutation:splice"),
        ("In_Frame_Del", "mutation:in_frame"),
    ]
    for mutation_type, expected_cat in cases:
        result = source.normalize({
            "uniqueMutationId": "test",
            "gene": {"hugoGeneSymbol": "TP53", "entrezGeneId": 7157},
            "proteinChange": "X1Y",
            "mutationType": mutation_type,
        })
        assert expected_cat in result["categories"], f"{mutation_type} should map to {expected_cat}"


@pytest.mark.asyncio
async def test_cbioportal_no_gene():
    """cBioPortal handles missing gene gracefully."""
    async with respx.mock:
        respx.get("https://www.cbioportal.org/api/genes/FAKE").respond(
            json={"hugoGeneSymbol": "FAKE"},
        )

        async with httpx.AsyncClient() as http:
            source = CBioPortalSource()
            results = await source.fetch("FAKE", http)

    assert results == []


@pytest.mark.asyncio
async def test_search_cbioportal_wrapper(cbioportal_response):
    """search_cbioportal wraps CBioPortalSource."""
    async with respx.mock:
        respx.get("https://www.cbioportal.org/api/genes/TP53").respond(
            json=cbioportal_response["gene"],
        )
        respx.get("https://www.cbioportal.org/api/mutations").respond(
            json=cbioportal_response["mutations"],
        )

        async with httpx.AsyncClient() as http:
            result = await search_cbioportal(http, "TP53")

    assert result["source"] == "cbioportal"
    assert result["total"] == 2
