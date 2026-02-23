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
async def test_clinvar_normalize_new_api():
    """ClinVar normalize handles new API format (post-2024) with split classifications."""
    source = ClinVarSource()
    raw = {
        "uid": "55555",
        "title": "NM_000546.6(TP53):c.524G>A (p.Arg175His)",
        "genes": [{"symbol": "TP53", "geneid": "7157"}],
        "variation_set": [{"variation_name": "p.Arg175His"}],
        "germline_classification": {
            "description": "Likely pathogenic",
            "review_status": "criteria provided, multiple submitters",
            "trait_set": [
                {"trait_name": "Li-Fraumeni syndrome 1"},
                {"trait_name": "Breast cancer"},
            ],
        },
        "oncogenicity_classification": {"description": ""},
        "clinical_impact_classification": {"description": ""},
    }
    result = source.normalize(raw)
    assert result["clinical_significance"] == "Likely pathogenic"
    assert result["review_status"] == "criteria provided, multiple submitters"
    assert "Li-Fraumeni syndrome 1" in result["conditions"]
    assert "Breast cancer" in result["conditions"]
    assert "cancer:likely_pathogenic" in result["categories"]
    assert result["gene_symbol"] == "TP53"


@pytest.mark.asyncio
async def test_clinvar_normalize_new_api_oncogenicity():
    """ClinVar normalize picks oncogenicity_classification when germline is empty."""
    source = ClinVarSource()
    raw = {
        "uid": "66666",
        "title": "test variant oncogenicity",
        "genes": [{"symbol": "BRAF"}],
        "variation_set": [{"variation_name": "V600E"}],
        "germline_classification": {"description": ""},
        "oncogenicity_classification": {
            "description": "Pathogenic",
            "review_status": "reviewed by expert panel",
            "trait_set": [{"trait_name": "Melanoma"}],
        },
        "clinical_impact_classification": {"description": ""},
    }
    result = source.normalize(raw)
    assert result["clinical_significance"] == "Pathogenic"
    assert result["review_status"] == "reviewed by expert panel"
    assert "Melanoma" in result["conditions"]
    assert "cancer:pathogenic_variant" in result["categories"]


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
