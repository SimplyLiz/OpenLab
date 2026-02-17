"""Tests for pipeline YAML validator."""

from openlab.paper.protocol_models import PipelineConfig, PipelineStage
from openlab.paper.validator import validate_config, validate_yaml


def test_valid_pipeline():
    """Valid pipeline passes validation."""
    yaml_str = """
pipeline:
  name: Test Pipeline
  description: A test
stages:
  - name: step1
    tool: STAR
  - name: step2
    tool: DESeq2
    depends_on:
      - step1
"""
    errors = validate_yaml(yaml_str)
    assert errors == []


def test_missing_pipeline_section():
    """Missing pipeline section is an error."""
    yaml_str = """
stages:
  - name: step1
"""
    errors = validate_yaml(yaml_str)
    assert any("pipeline" in e.lower() for e in errors)


def test_missing_pipeline_name():
    """Missing pipeline name is an error."""
    yaml_str = """
pipeline:
  description: no name
stages:
  - name: step1
"""
    errors = validate_yaml(yaml_str)
    assert any("name" in e.lower() for e in errors)


def test_empty_stages():
    """Empty stages list is an error."""
    yaml_str = """
pipeline:
  name: Test
stages: []
"""
    errors = validate_yaml(yaml_str)
    assert any("no stages" in e.lower() for e in errors)


def test_duplicate_stage_names():
    """Duplicate stage names are caught."""
    yaml_str = """
pipeline:
  name: Test
stages:
  - name: step1
  - name: step1
"""
    errors = validate_yaml(yaml_str)
    assert any("duplicate" in e.lower() for e in errors)


def test_missing_stage_name():
    """Stages without names are caught."""
    yaml_str = """
pipeline:
  name: Test
stages:
  - tool: STAR
"""
    errors = validate_yaml(yaml_str)
    assert any("missing 'name'" in e.lower() for e in errors)


def test_nonexistent_dependency():
    """References to nonexistent stages are caught."""
    yaml_str = """
pipeline:
  name: Test
stages:
  - name: step1
    depends_on:
      - nonexistent
"""
    errors = validate_yaml(yaml_str)
    assert any("does not exist" in e.lower() for e in errors)


def test_circular_dependency():
    """Circular dependencies are detected."""
    yaml_str = """
pipeline:
  name: Test
stages:
  - name: step1
    depends_on:
      - step2
  - name: step2
    depends_on:
      - step1
"""
    errors = validate_yaml(yaml_str)
    assert any("circular" in e.lower() for e in errors)


def test_invalid_yaml():
    """Invalid YAML is caught."""
    yaml_str = "{{{{not valid yaml"
    errors = validate_yaml(yaml_str)
    assert len(errors) > 0


def test_validate_config():
    """validate_config works with PipelineConfig objects."""
    config = PipelineConfig(
        name="Test",
        stages=[PipelineStage(name="step1", tool="STAR")],
    )
    errors = validate_config(config)
    assert errors == []
