"""Agent-related ORM models — agent runs, provenance logs, claims."""

from __future__ import annotations

import enum

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openlab.db.models.base import Base, TimestampMixin


class AgentRunStatusDB(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    gene_symbol: Mapped[str] = mapped_column(String(50), index=True)
    cancer_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(AgentRunStatusDB, native_enum=False),
        default=AgentRunStatusDB.PENDING,
    )
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    dossier_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    provenance_logs: Mapped[list["ProvenanceLog"]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan"
    )
    claim_records: Mapped[list["ClaimRecord"]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan"
    )


class ProvenanceLog(TimestampMixin, Base):
    __tablename__ = "provenance_logs"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("agent_runs.run_id"), index=True
    )
    call_id: Mapped[str] = mapped_column(String(24), index=True)
    tool_name: Mapped[str] = mapped_column(String(100))
    arguments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    completed_at: Mapped[str | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(default=True)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    parent_call_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="provenance_logs")

    __table_args__ = (
        Index("ix_provenance_logs_run_id_call_id", "run_id", "call_id"),
    )


class CitationStatusDB(str, enum.Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNCHECKED = "unchecked"


class ClaimRecord(TimestampMixin, Base):
    __tablename__ = "claim_records"

    claim_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("agent_runs.run_id"), index=True
    )
    claim_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    citation_status: Mapped[str] = mapped_column(
        Enum(CitationStatusDB, native_enum=False),
        default=CitationStatusDB.UNCHECKED,
    )
    is_speculative: Mapped[bool] = mapped_column(default=False)
    section_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="claim_records")
