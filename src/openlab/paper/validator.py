"""Validate generated pipeline YAML configurations."""

from __future__ import annotations

import logging

import yaml

from openlab.paper.protocol_models import PipelineConfig

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when pipeline validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Pipeline validation failed: {'; '.join(errors)}")


def validate_yaml(yaml_str: str) -> list[str]:
    """Validate a YAML pipeline configuration.

    Returns a list of validation errors (empty = valid).
    """
    errors: list[str] = []

    # Parse YAML
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        return [f"Invalid YAML: {e}"]

    if not isinstance(data, dict):
        return ["YAML root must be a mapping"]

    # Check required top-level keys
    if "pipeline" not in data:
        errors.append("Missing 'pipeline' section")
    elif not isinstance(data["pipeline"], dict):
        errors.append("'pipeline' must be a mapping")
    else:
        if "name" not in data["pipeline"]:
            errors.append("Pipeline missing 'name'")

    # Check stages
    stages = data.get("stages", [])
    if not isinstance(stages, list):
        errors.append("'stages' must be a list")
        return errors

    if not stages:
        errors.append("Pipeline has no stages")
        return errors

    stage_names = set()
    for i, stage in enumerate(stages):
        if not isinstance(stage, dict):
            errors.append(f"Stage {i}: must be a mapping")
            continue

        name = stage.get("name", "")
        if not name:
            errors.append(f"Stage {i}: missing 'name'")
        elif name in stage_names:
            errors.append(f"Stage {i}: duplicate name '{name}'")
        stage_names.add(name)

    # Check for circular dependencies
    cycle_errors = _check_cycles(stages)
    errors.extend(cycle_errors)

    # Check that depends_on references exist
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        deps = stage.get("depends_on", [])
        if isinstance(deps, list):
            for dep in deps:
                if dep not in stage_names:
                    errors.append(
                        f"Stage '{stage.get('name', '?')}': depends_on '{dep}' does not exist"
                    )

    return errors


def validate_config(config: PipelineConfig) -> list[str]:
    """Validate a PipelineConfig object."""
    from openlab.paper.yaml_generator import generate_yaml
    yaml_str = generate_yaml(config)
    return validate_yaml(yaml_str)


def _check_cycles(stages: list[dict]) -> list[str]:
    """Check for circular dependencies in pipeline stages."""
    # Build adjacency list
    graph: dict[str, list[str]] = {}
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        name = stage.get("name", "")
        deps = stage.get("depends_on", [])
        if isinstance(deps, list):
            graph[name] = deps
        else:
            graph[name] = []

    # DFS cycle detection
    visited: set[str] = set()
    in_stack: set[str] = set()
    errors: list[str] = []

    def dfs(node: str) -> bool:
        visited.add(node)
        in_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in in_stack:
                errors.append(f"Circular dependency detected involving '{node}' -> '{neighbor}'")
                return True
        in_stack.discard(node)
        return False

    for node in graph:
        if node not in visited:
            dfs(node)

    return errors
