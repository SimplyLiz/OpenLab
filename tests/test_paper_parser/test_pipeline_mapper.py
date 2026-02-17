"""Tests for pipeline mapper."""

from openlab.paper.pipeline_mapper import _slugify, map_protocol_to_pipeline
from openlab.paper.protocol_models import ExtractedProtocol, ProtocolStep


def _make_protocol(steps: list[tuple[str, str]]) -> ExtractedProtocol:
    """Helper: create protocol with (technique, description) pairs."""
    return ExtractedProtocol(
        title="Test Protocol",
        steps=[
            ProtocolStep(step_number=i + 1, technique=tech, description=desc)
            for i, (tech, desc) in enumerate(steps)
        ],
    )


def test_map_known_techniques():
    """Known techniques map to pipeline stages."""
    protocol = _make_protocol([
        ("RNA-seq", "Sequencing"),
        ("differential expression", "DE analysis"),
        ("gene set enrichment", "GSEA"),
    ])
    pipeline = map_protocol_to_pipeline(protocol)
    assert len(pipeline.stages) == 3
    assert pipeline.stages[0].tool  # Should have a mapped tool
    assert not pipeline.warnings  # No unmappable steps


def test_map_unknown_technique():
    """Unknown techniques get manual_review flag."""
    protocol = _make_protocol([
        ("novel_assay_xyz", "Some custom technique"),
    ])
    pipeline = map_protocol_to_pipeline(protocol)
    assert len(pipeline.stages) == 1
    assert pipeline.stages[0].manual_review is True
    assert "TODO" in pipeline.stages[0].notes
    assert len(pipeline.warnings) == 1


def test_map_dependencies():
    """Pipeline stages have sequential dependencies."""
    protocol = _make_protocol([
        ("RNA-seq", "Sequencing"),
        ("differential expression", "DE analysis"),
    ])
    pipeline = map_protocol_to_pipeline(protocol)
    assert pipeline.stages[1].depends_on == [pipeline.stages[0].name]


def test_map_wet_lab_techniques():
    """Wet lab techniques are marked for manual review."""
    protocol = _make_protocol([
        ("cell culture", "Culture cells"),
        ("western blot", "Detect protein"),
        ("PCR", "Amplify DNA"),
    ])
    pipeline = map_protocol_to_pipeline(protocol)
    for stage in pipeline.stages:
        assert stage.manual_review is True


def test_map_empty_protocol():
    """Empty protocol produces empty pipeline."""
    protocol = ExtractedProtocol()
    pipeline = map_protocol_to_pipeline(protocol)
    assert len(pipeline.stages) == 0


def test_slugify():
    """Slugify produces valid stage names."""
    assert _slugify("RNA-seq") == "rna_seq"
    assert _slugify("ChIP-seq Analysis") == "chip_seq_analysis"
    assert _slugify("") == "unnamed"


def test_map_case_insensitive():
    """Technique matching is case-insensitive."""
    protocol = _make_protocol([
        ("rna-seq", "sequencing"),
        ("CHIP-SEQ", "chip"),
    ])
    pipeline = map_protocol_to_pipeline(protocol)
    assert all(s.tool for s in pipeline.stages)
