"""Pydantic models for extracted protocols and pipeline configs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProtocolStep(BaseModel):
    """A single step extracted from a methods section."""
    step_number: int = 0
    technique: str = ""
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    reagents: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    duration: str = ""
    temperature: str = ""
    notes: str = ""
    confidence: float = 0.0  # How confident the parser is about this step


class Reagent(BaseModel):
    """A reagent mentioned in the methods."""
    name: str
    concentration: str = ""
    volume: str = ""
    supplier: str = ""
    catalog_number: str = ""


class ExtractedProtocol(BaseModel):
    """Structured representation of a methods section."""
    title: str = ""
    paper_doi: str = ""
    steps: list[ProtocolStep] = Field(default_factory=list)
    reagents: list[Reagent] = Field(default_factory=list)
    organisms: list[str] = Field(default_factory=list)
    techniques_mentioned: list[str] = Field(default_factory=list)
    raw_methods_text: str = ""


class PipelineStage(BaseModel):
    """A stage in a computational pipeline."""
    name: str
    tool: str = ""
    description: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    manual_review: bool = False
    notes: str = ""


class PipelineConfig(BaseModel):
    """Complete pipeline configuration generated from a paper."""
    name: str = ""
    description: str = ""
    source_paper: str = ""
    source_doi: str = ""
    stages: list[PipelineStage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
