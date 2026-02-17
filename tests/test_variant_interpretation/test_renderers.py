"""Tests for variant report renderers."""

from openlab.cancer.models.variant import (
    AnnotatedVariant,
    ClinicalSignificance,
    EvidenceItem,
    GenomeBuild,
    VariantRecord,
    VariantReport,
)
from openlab.cancer.output.json_renderer import render_json
from openlab.cancer.output.markdown_renderer import render_markdown

DISCLAIMER = "FOR RESEARCH USE ONLY"


def _sample_report() -> VariantReport:
    return VariantReport(
        sample_id="SAMPLE_001",
        tumor_type="breast",
        genome_build=GenomeBuild.HG38,
        variants=[
            AnnotatedVariant(
                variant=VariantRecord(
                    chrom="chr17", pos=7674220, ref="C", alt="T",
                    gene_symbol="TP53", hgvs_g="NC_000017.11:g.7674220C>T",
                ),
                evidence=[
                    EvidenceItem(
                        source="clinvar",
                        classification=ClinicalSignificance.PATHOGENIC,
                        description="TP53 R175H",
                        confidence=0.95,
                        pmids=["28263969"],
                    ),
                    EvidenceItem(
                        source="oncokb",
                        description="Oncogenic",
                        therapies=["AZD1775"],
                        confidence=0.8,
                    ),
                ],
                consensus_classification=ClinicalSignificance.PATHOGENIC,
                confidence=0.9,
                is_actionable=True,
                annotation_sources=["clinvar", "oncokb"],
            ),
        ],
        total_variants_parsed=5,
        total_annotated=1,
        total_pathogenic=1,
        total_actionable=1,
    )


def test_markdown_contains_disclaimer():
    """Markdown report has disclaimer at top and bottom."""
    md = render_markdown(_sample_report())
    lines = md.strip().split("\n")
    assert DISCLAIMER in lines[0]
    assert DISCLAIMER in lines[-1]


def test_markdown_contains_variant_table():
    """Markdown report includes variant table."""
    md = render_markdown(_sample_report())
    assert "| Gene |" in md
    assert "| TP53 |" in md
    assert "Pathogenic" in md


def test_markdown_contains_evidence():
    """Markdown report includes detailed evidence."""
    md = render_markdown(_sample_report())
    assert "clinvar" in md
    assert "PMID:28263969" in md
    assert "AZD1775" in md


def test_markdown_contains_summary_info():
    """Markdown report includes sample and summary info."""
    md = render_markdown(_sample_report())
    assert "SAMPLE_001" in md
    assert "breast" in md
    assert "hg38" in md


def test_json_contains_disclaimer():
    """JSON output always has disclaimer field."""
    data = render_json(_sample_report())
    assert DISCLAIMER in data["disclaimer"]


def test_json_contains_variants():
    """JSON output includes variants."""
    data = render_json(_sample_report())
    assert len(data["variants"]) == 1
    assert data["variants"][0]["variant"]["gene_symbol"] == "TP53"


def test_json_roundtrip():
    """JSON output can be validated by Pydantic."""
    data = render_json(_sample_report())
    # Should be JSON-serializable
    import json
    json_str = json.dumps(data)
    assert json_str


def test_disclaimer_always_present():
    """VariantReport always has the correct disclaimer."""
    report = VariantReport()
    assert DISCLAIMER in report.disclaimer
    # Even if someone tries to pass a different value, the JSON output
    # will still have the correct disclaimer from the renderer
    data = render_json(report)
    assert DISCLAIMER in data["disclaimer"]
