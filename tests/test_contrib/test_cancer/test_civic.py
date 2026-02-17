"""Tests for CIViC cancer evidence source."""

import httpx
import pytest
import respx

from openlab.contrib.cancer.sources.civic import CIViCSource, search_civic


@pytest.mark.asyncio
async def test_civic_fetch(civic_response):
    """CIViC fetch returns gene + evidence items."""
    async with respx.mock:
        respx.post("https://civicdb.org/api/graphql").respond(
            json=civic_response,
        )

        async with httpx.AsyncClient() as http:
            source = CIViCSource()
            results = await source.fetch("TP53", http)

    # 1 gene record + 2 evidence items
    assert len(results) == 3
    gene_records = [r for r in results if r.get("record_type") == "gene"]
    evidence_records = [r for r in results if r.get("record_type") == "evidence"]
    assert len(gene_records) == 1
    assert len(evidence_records) == 2

    # Gene-level
    assert gene_records[0]["name"] == "TP53"
    assert gene_records[0]["variant_count"] == 85
    assert "cancer:curated_evidence" in gene_records[0]["categories"]

    # Evidence: predictive with drug
    ev1 = evidence_records[0]
    assert ev1["evidence_type"] == "PREDICTIVE"
    assert "cancer:drug_target" in ev1["categories"]
    assert "cancer:drug_sensitive" in ev1["categories"]
    assert ev1["pmid"] == "28263969"
    assert "AZD1775" in ev1["therapies"]


@pytest.mark.asyncio
async def test_civic_normalize_evidence_types():
    """CIViC normalizes different evidence types."""
    source = CIViCSource()

    cases = [
        ("PREDICTIVE", "cancer:drug_target"),
        ("DIAGNOSTIC", "cancer:diagnostic_marker"),
        ("PROGNOSTIC", "cancer:prognostic_marker"),
        ("PREDISPOSING", "cancer:risk_factor"),
    ]
    for ev_type, expected_cat in cases:
        result = source.normalize({
            "id": 1,
            "evidenceType": ev_type,
            "evidenceLevel": "B",
            "status": "accepted",
            "significance": "",
            "description": "test",
            "therapies": [],
            "disease": {"name": "Cancer", "doid": "162"},
            "source": {"citationId": "12345", "sourceType": "PUBMED"},
        })
        assert expected_cat in result["categories"], f"{ev_type} should map to {expected_cat}"


@pytest.mark.asyncio
async def test_civic_empty_gene():
    """CIViC handles unknown gene gracefully."""
    async with respx.mock:
        respx.post("https://civicdb.org/api/graphql").respond(
            json={"data": {"genes": {"nodes": []}}},
        )

        async with httpx.AsyncClient() as http:
            source = CIViCSource()
            results = await source.fetch("NONEXISTENT", http)

    assert results == []


@pytest.mark.asyncio
async def test_search_civic_wrapper(civic_response):
    """search_civic wraps CIViCSource."""
    async with respx.mock:
        respx.post("https://civicdb.org/api/graphql").respond(
            json=civic_response,
        )

        async with httpx.AsyncClient() as http:
            result = await search_civic(http, "TP53")

    assert result["source"] == "civic"
    assert result["total"] == 3
