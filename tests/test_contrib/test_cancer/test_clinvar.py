"""Tests for ClinVar cancer evidence source."""

import httpx
import pytest
import respx

from openlab.contrib.cancer.sources.clinvar import ClinVarSource, search_clinvar


@pytest.mark.asyncio
async def test_clinvar_fetch(clinvar_response):
    """ClinVar fetch returns normalized variants."""
    esearch_resp = {"esearchresult": clinvar_response["esearchresult"]}
    esummary_resp = {"result": clinvar_response["result"]}

    async with respx.mock:
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").respond(
            json=esearch_resp,
        )
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").respond(
            json=esummary_resp,
        )

        async with httpx.AsyncClient() as http:
            source = ClinVarSource()
            results = await source.fetch("TP53", http)

    assert len(results) == 2
    assert results[0]["source"] == "clinvar"
    assert results[0]["variant_id"] == "12345"
    assert results[0]["gene_symbol"] == "TP53"
    assert "cancer:pathogenic_variant" in results[0]["categories"]


@pytest.mark.asyncio
async def test_clinvar_normalize():
    """ClinVar normalize extracts clinical significance categories."""
    source = ClinVarSource()
    raw = {
        "uid": "99999",
        "title": "test variant",
        "clinical_significance": {"description": "Pathogenic/Likely pathogenic"},
        "review_status": "criteria provided",
        "genes": [{"symbol": "BRCA1"}],
        "variation_set": [{"variation_name": "c.5266dupC"}],
        "trait_set": [{"trait_name": "Breast-ovarian cancer"}],
    }
    result = source.normalize(raw)
    assert result["gene_symbol"] == "BRCA1"
    assert "cancer:pathogenic_variant" in result["categories"]
    assert "cancer:likely_pathogenic" in result["categories"]


@pytest.mark.asyncio
async def test_clinvar_empty_response():
    """ClinVar returns empty list when no results."""
    async with respx.mock:
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").respond(
            json={"esearchresult": {"count": "0", "idlist": []}},
        )

        async with httpx.AsyncClient() as http:
            source = ClinVarSource()
            results = await source.fetch("NONEXISTENT_GENE", http)

    assert results == []


@pytest.mark.asyncio
async def test_search_clinvar_wrapper():
    """search_clinvar wraps ClinVarSource with error handling."""
    async with respx.mock:
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").respond(
            json={"esearchresult": {"count": "0", "idlist": []}},
        )

        async with httpx.AsyncClient() as http:
            result = await search_clinvar(http, "TP53")

    assert result["source"] == "clinvar"
    assert result["gene_symbol"] == "TP53"
    assert isinstance(result["variants"], list)
