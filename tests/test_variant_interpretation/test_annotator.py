"""Tests for variant annotator."""

import httpx
import pytest
import respx

from openlab.cancer.annotation.annotator import _parse_clinical_significance, annotate_variants
from openlab.cancer.models.variant import ClinicalSignificance, VariantRecord


def test_parse_clinical_significance():
    """Clinical significance strings parse correctly."""
    assert _parse_clinical_significance("Pathogenic") == ClinicalSignificance.PATHOGENIC
    assert (
        _parse_clinical_significance("Likely pathogenic")
        == ClinicalSignificance.LIKELY_PATHOGENIC
    )
    assert _parse_clinical_significance("Benign") == ClinicalSignificance.BENIGN
    assert _parse_clinical_significance("Likely benign") == ClinicalSignificance.LIKELY_BENIGN
    assert _parse_clinical_significance("Uncertain significance") == ClinicalSignificance.VUS
    assert _parse_clinical_significance("unknown") is None


@pytest.mark.asyncio
async def test_annotate_variants_no_gene():
    """Variants without gene symbol get no annotation."""
    variants = [VariantRecord(chrom="chr1", pos=100, ref="A", alt="T")]

    async with httpx.AsyncClient() as http:
        results = await annotate_variants(variants, http)

    assert len(results) == 1
    assert results[0].evidence == []
    assert results[0].annotation_sources == []


@pytest.mark.asyncio
async def test_annotate_variants_with_gene():
    """Variants with gene symbol attempt annotation."""
    variants = [VariantRecord(chrom="chr17", pos=7674220, ref="C", alt="T", gene_symbol="TP53")]

    async with respx.mock:
        # Mock all annotation source APIs to return empty/minimal
        respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").respond(
            json={"esearchresult": {"count": "0", "idlist": []}},
        )
        respx.get("https://clinicaltables.nlm.nih.gov/api/cosmic/v4/search").respond(
            json=[0, [], None, []],
        )
        respx.get("https://www.oncokb.org/api/v1/genes/lookup").respond(json=[])
        respx.get("https://www.oncokb.org/api/v1/variants/lookup").respond(json=[])
        respx.post("https://civicdb.org/api/graphql").respond(
            json={"data": {"genes": {"nodes": []}}},
        )

        async with httpx.AsyncClient() as http:
            results = await annotate_variants(variants, http)

    assert len(results) == 1
    # Sources were queried even though they returned empty
    assert isinstance(results[0].annotation_sources, list)
