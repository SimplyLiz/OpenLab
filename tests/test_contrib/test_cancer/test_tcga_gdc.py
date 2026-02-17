"""Tests for TCGA/GDC cancer evidence source."""

import httpx
import pytest
import respx

from openlab.contrib.cancer.sources.tcga_gdc import TcgaGdcSource, search_tcga_gdc


@pytest.mark.asyncio
async def test_tcga_gdc_fetch(gdc_response):
    """GDC fetch returns normalized SSM hits."""
    async with respx.mock:
        respx.get("https://api.gdc.cancer.gov/ssms").respond(
            json=gdc_response,
        )

        async with httpx.AsyncClient() as http:
            source = TcgaGdcSource()
            results = await source.fetch("TP53", http)

    assert len(results) == 2
    assert results[0]["source"] == "tcga_gdc"
    assert results[0]["gene_symbol"] == "TP53"
    assert results[0]["aa_change"] == "R175H"
    assert results[0]["project_count"] == 3
    assert "TCGA-BRCA" in results[0]["projects"]
    assert "mutation:missense" in results[0]["categories"]

    # Second hit: stop_gained
    assert results[1]["consequence_type"] == "stop_gained"
    assert "mutation:loss_of_function" in results[1]["categories"]


@pytest.mark.asyncio
async def test_tcga_gdc_normalize():
    """GDC normalize extracts project counts correctly."""
    source = TcgaGdcSource()
    raw = {
        "ssm_id": "test_ssm",
        "genomic_dna_change": "chr1:g.100A>T",
        "consequence": [{
            "transcript": {
                "gene": {"symbol": "TEST"},
                "consequence_type": "splice_donor_variant",
                "aa_change": "",
            }
        }],
        "occurrence": [
            {"case": {"project": {"project_id": "TCGA-BRCA"}}},
            {"case": {"project": {"project_id": "TCGA-BRCA"}}},
            {"case": {"project": {"project_id": "TCGA-LUAD"}}},
        ],
    }
    result = source.normalize(raw)
    assert result["project_count"] == 2  # deduplicated
    assert result["case_count"] == 3
    assert "mutation:splice" in result["categories"]


@pytest.mark.asyncio
async def test_tcga_gdc_empty_response():
    """GDC returns empty for no hits."""
    async with respx.mock:
        respx.get("https://api.gdc.cancer.gov/ssms").respond(
            json={"data": {"hits": [], "pagination": {"count": 0, "total": 0}}},
        )

        async with httpx.AsyncClient() as http:
            source = TcgaGdcSource()
            results = await source.fetch("NONEXISTENT", http)

    assert results == []


@pytest.mark.asyncio
async def test_search_tcga_gdc_wrapper(gdc_response):
    """search_tcga_gdc wraps TcgaGdcSource."""
    async with respx.mock:
        respx.get("https://api.gdc.cancer.gov/ssms").respond(
            json=gdc_response,
        )

        async with httpx.AsyncClient() as http:
            result = await search_tcga_gdc(http, "TP53")

    assert result["source"] == "tcga_gdc"
    assert result["total"] == 2
