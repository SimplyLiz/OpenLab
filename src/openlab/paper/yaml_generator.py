"""YAML pipeline configuration generator."""

from __future__ import annotations

from typing import Any

import yaml

from openlab.paper.protocol_models import PipelineConfig


def generate_yaml(config: PipelineConfig) -> str:
    """Generate YAML from a PipelineConfig."""
    data = _config_to_dict(config)
    result: str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return result


def _config_to_dict(config: PipelineConfig) -> dict[str, Any]:
    """Convert PipelineConfig to a YAML-friendly dict."""
    stages = []
    for stage in config.stages:
        stage_dict: dict[str, Any] = {
            "name": stage.name,
        }
        if stage.tool:
            stage_dict["tool"] = stage.tool
        if stage.description:
            stage_dict["description"] = stage.description
        if stage.inputs:
            stage_dict["inputs"] = stage.inputs
        if stage.outputs:
            stage_dict["outputs"] = stage.outputs
        if stage.parameters:
            stage_dict["parameters"] = stage.parameters
        if stage.depends_on:
            stage_dict["depends_on"] = stage.depends_on
        if stage.manual_review:
            stage_dict["manual_review"] = True
        if stage.notes:
            stage_dict["notes"] = stage.notes
        stages.append(stage_dict)

    result: dict[str, Any] = {
        "pipeline": {
            "name": config.name,
            "description": config.description,
        },
    }
    if config.source_doi:
        result["pipeline"]["source_doi"] = config.source_doi

    result["stages"] = stages

    if config.warnings:
        result["warnings"] = config.warnings

    return result
