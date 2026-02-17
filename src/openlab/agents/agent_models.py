"""Pydantic models for the agent framework — Layer 0 (no internal deps)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentEventType(StrEnum):
    PLAN_CREATED = "plan_created"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_COMPLETED = "synthesis_completed"
    CRITIC_STARTED = "critic_started"
    CRITIC_COMPLETED = "critic_completed"
    CLAIM_EXTRACTED = "claim_extracted"
    DOSSIER_COMPLETED = "dossier_completed"
    RUN_FAILED = "run_failed"
    PROGRESS = "progress"


class AgentEvent(BaseModel):
    """Mirrors the PipelineEvent pattern for agent streaming."""

    event_type: AgentEventType
    stage: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    progress: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str = ""


class ToolCall(BaseModel):
    call_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    parent_call_id: str | None = None


class ToolResult(BaseModel):
    call_id: str
    tool_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    error: str | None = None


class ProvenanceEntry(BaseModel):
    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    success: bool = True
    sources: list[str] = Field(default_factory=list)
    parent_call_id: str | None = None
    error: str | None = None


class CitationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    UNCHECKED = "unchecked"


class Claim(BaseModel):
    claim_text: str
    confidence: float = 0.0
    citations: list[str] = Field(default_factory=list)
    citation_status: CitationStatus = CitationStatus.UNCHECKED
    is_speculative: bool = False


class DossierSection(BaseModel):
    title: str
    content: str  # Markdown
    claims: list[Claim] = Field(default_factory=list)
    tool_calls_used: list[str] = Field(default_factory=list)


class GeneDossier(BaseModel):
    gene_symbol: str
    ncbi_gene_id: str | None = None
    ensembl_id: str | None = None
    chromosome: str | None = None
    cancer_type: str | None = None
    sections: list[DossierSection] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    provenance: list[ProvenanceEntry] = Field(default_factory=list)
    convergence_score: float = 0.0


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    status: AgentRunStatus = AgentRunStatus.PENDING
    gene_symbol: str = ""
    cancer_type: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_tool_calls: int = 0
    error: str | None = None
