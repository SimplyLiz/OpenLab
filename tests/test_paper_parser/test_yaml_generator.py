"""Tests for YAML generator."""

import yaml

from openlab.paper.protocol_models import PipelineConfig, PipelineStage
from openlab.paper.yaml_generator import generate_yaml


def _sample_config() -> PipelineConfig:
    return PipelineConfig(
        name="Test Pipeline",
        description="A test pipeline",
        source_doi="10.1234/test",
        stages=[
            PipelineStage(
                name="alignment",
                tool="STAR",
                description="Align reads",
                inputs=["fastq_r1", "fastq_r2"],
                outputs=["aligned_bam"],
            ),
            PipelineStage(
                name="quantification",
                tool="featureCounts",
                description="Count features",
                inputs=["aligned_bam"],
                outputs=["counts"],
                depends_on=["alignment"],
            ),
        ],
    )


def test_generate_yaml_valid():
    """Generated YAML is valid."""
    yaml_str = generate_yaml(_sample_config())
    data = yaml.safe_load(yaml_str)
    assert data is not None
    assert "pipeline" in data
    assert "stages" in data


def test_generate_yaml_pipeline_info():
    """Pipeline section contains name and description."""
    yaml_str = generate_yaml(_sample_config())
    data = yaml.safe_load(yaml_str)
    assert data["pipeline"]["name"] == "Test Pipeline"
    assert data["pipeline"]["source_doi"] == "10.1234/test"


def test_generate_yaml_stages():
    """Stages are correctly represented."""
    yaml_str = generate_yaml(_sample_config())
    data = yaml.safe_load(yaml_str)
    stages = data["stages"]
    assert len(stages) == 2
    assert stages[0]["name"] == "alignment"
    assert stages[0]["tool"] == "STAR"
    assert stages[1]["depends_on"] == ["alignment"]


def test_generate_yaml_warnings():
    """Warnings are included in output."""
    config = PipelineConfig(
        name="Test",
        stages=[PipelineStage(name="step1")],
        warnings=["Could not map step 3"],
    )
    yaml_str = generate_yaml(config)
    data = yaml.safe_load(yaml_str)
    assert "warnings" in data
    assert len(data["warnings"]) == 1


def test_generate_yaml_empty_pipeline():
    """Empty pipeline generates valid but minimal YAML."""
    config = PipelineConfig(name="Empty")
    yaml_str = generate_yaml(config)
    data = yaml.safe_load(yaml_str)
    assert data["pipeline"]["name"] == "Empty"
    assert data["stages"] == []
