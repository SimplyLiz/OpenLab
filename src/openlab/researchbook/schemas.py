"""Pydantic v2 schemas for the ResearchBook API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ThreadListItem(BaseModel):
    thread_id: int
    title: str
    summary: str | None = None
    status: str
    gene_symbol: str
    cancer_type: str | None = None
    convergence_score: float = 0.0
    confidence_tier: int = 3
    comment_count: int = 0
    challenge_count: int = 0
    fork_count: int = 0
    created_at: datetime | None = None


class ThreadDetail(ThreadListItem):
    agent_run_id: str | None = None
    forked_from_id: int | None = None
    claims_snapshot: list[dict[str, Any]] | None = None
    evidence_snapshot: list[dict[str, Any]] | None = None
    comments: list[CommentRecord] = Field(default_factory=list)
    forks: list[ForkRecord] = Field(default_factory=list)


class CommentRecord(BaseModel):
    comment_id: int
    author_name: str
    body: str
    comment_type: str
    reply_to_comment_id: int | None = None
    referenced_claim_ids: list[int] | None = None
    created_at: datetime | None = None


class ForkRecord(BaseModel):
    fork_id: int
    child_thread_id: int
    modification_summary: str | None = None
    modification_params: dict[str, Any] | None = None


class ThreadCreate(BaseModel):
    agent_run_id: str
    title: str | None = None
    gene_symbol: str | None = None
    cancer_type: str | None = None


class CommentCreate(BaseModel):
    author_name: str
    body: str
    comment_type: str = "comment"
    reply_to_comment_id: int | None = None
    referenced_claim_ids: list[int] | None = None


class ChallengeCreate(BaseModel):
    author_name: str
    body: str
    referenced_claim_ids: list[int] | None = None


class CorrectionCreate(BaseModel):
    author_name: str
    body: str
    correction_details: dict[str, Any] = Field(default_factory=dict)
    referenced_claim_ids: list[int] | None = None


class ForkCreate(BaseModel):
    gene_symbol: str | None = None
    cancer_type: str | None = None
    modification_summary: str | None = None
    modification_params: dict[str, Any] = Field(default_factory=dict)


class FeedQuery(BaseModel):
    page: int = 1
    per_page: int = 20
    gene_symbol: str | None = None
    cancer_type: str | None = None
    status: str | None = None
    sort_by: str = "recent"
    query: str | None = None


# Forward reference resolution
ThreadDetail.model_rebuild()
