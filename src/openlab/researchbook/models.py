"""ResearchBook SQLAlchemy models."""

from __future__ import annotations

import enum

from sqlalchemy import JSON, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openlab.db.models.base import Base, TimestampMixin


class ThreadStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CHALLENGED = "challenged"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class CommentType(enum.StrEnum):
    COMMENT = "comment"
    CHALLENGE = "challenge"
    CORRECTION = "correction"
    ENDORSEMENT = "endorsement"


class NotifyOn(enum.StrEnum):
    ALL = "all"
    CHALLENGES = "challenges"
    CORRECTIONS = "corrections"


class ResearchThread(TimestampMixin, Base):
    __tablename__ = "research_threads"

    thread_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(ThreadStatus, native_enum=False), default=ThreadStatus.DRAFT
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("agent_runs.run_id"), nullable=True, index=True
    )
    gene_symbol: Mapped[str] = mapped_column(String(50), index=True)
    cancer_type: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    forked_from_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("research_threads.thread_id"), nullable=True
    )
    claims_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evidence_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    convergence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_tier: Mapped[int] = mapped_column(Integer, default=3)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    challenge_count: Mapped[int] = mapped_column(Integer, default=0)
    fork_count: Mapped[int] = mapped_column(Integer, default=0)

    comments: Mapped[list[HumanComment]] = relationship(
        back_populates="thread", cascade="all, delete-orphan",
        foreign_keys="HumanComment.thread_id",
    )
    child_forks: Mapped[list[ThreadFork]] = relationship(
        back_populates="parent_thread",
        foreign_keys="ThreadFork.parent_thread_id",
    )
    watchers: Mapped[list[ThreadWatcher]] = relationship(
        back_populates="thread", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_research_threads_status", "status"),
        Index("ix_research_threads_gene_cancer", "gene_symbol", "cancer_type"),
    )


class HumanComment(TimestampMixin, Base):
    __tablename__ = "human_comments"

    comment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_threads.thread_id"), index=True
    )
    author_name: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    comment_type: Mapped[str] = mapped_column(
        Enum(CommentType, native_enum=False), default=CommentType.COMMENT
    )
    reply_to_comment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("human_comments.comment_id"), nullable=True
    )
    referenced_claim_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    thread: Mapped[ResearchThread] = relationship(
        back_populates="comments", foreign_keys=[thread_id]
    )


class ThreadFork(TimestampMixin, Base):
    __tablename__ = "thread_forks"

    fork_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_threads.thread_id"), index=True
    )
    child_thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_threads.thread_id"), unique=True
    )
    modification_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    modification_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    parent_thread: Mapped[ResearchThread] = relationship(
        foreign_keys=[parent_thread_id], back_populates="child_forks"
    )
    child_thread: Mapped[ResearchThread] = relationship(foreign_keys=[child_thread_id])


class ThreadWatcher(TimestampMixin, Base):
    __tablename__ = "thread_watchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_threads.thread_id"), index=True
    )
    watcher_name: Mapped[str] = mapped_column(String(200))
    notify_on: Mapped[str] = mapped_column(
        Enum(NotifyOn, native_enum=False), default=NotifyOn.ALL
    )

    thread: Mapped[ResearchThread] = relationship(back_populates="watchers")
