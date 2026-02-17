"""ResearchBook service — stateless functions for thread management."""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from openlab.researchbook.models import (
    CommentType,
    HumanComment,
    ResearchThread,
    ThreadFork,
    ThreadStatus,
    ThreadWatcher,
)


def create_thread_from_agent_run(
    db: Session,
    agent_run_id: str,
    title: str | None = None,
    gene_symbol: str | None = None,
    cancer_type: str | None = None,
) -> ResearchThread:
    """Create a DRAFT thread from a completed agent run."""
    from openlab.db.models.agent import AgentRun

    run = db.query(AgentRun).filter(AgentRun.run_id == agent_run_id).first()
    gene = gene_symbol or (run.gene_symbol if run else "unknown")
    cancer = cancer_type or (run.cancer_type if run else None)

    dossier = run.dossier_json if run else None
    claims = dossier.get("claims", []) if isinstance(dossier, dict) else []

    thread = ResearchThread(
        title=title or f"Dossier: {gene} in {cancer or 'general'} cancer",
        status=ThreadStatus.DRAFT,
        agent_run_id=agent_run_id,
        gene_symbol=gene,
        cancer_type=cancer,
        claims_snapshot=claims,
        evidence_snapshot=dossier.get("provenance", []) if isinstance(dossier, dict) else [],
        convergence_score=(
            dossier.get("convergence_score", 0.0) if isinstance(dossier, dict) else 0.0
        ),
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


def publish_thread(db: Session, thread_id: int) -> ResearchThread:
    """Transition DRAFT -> PUBLISHED."""
    thread = db.query(ResearchThread).filter(ResearchThread.thread_id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")
    if thread.status != ThreadStatus.DRAFT.value:
        raise ValueError(f"Thread {thread_id} is not in DRAFT status")
    thread.status = ThreadStatus.PUBLISHED
    db.commit()
    db.refresh(thread)
    return thread


def list_feed(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    gene_symbol: str | None = None,
    cancer_type: str | None = None,
    status: str | None = None,
    sort_by: str = "recent",
) -> tuple[list[ResearchThread], int]:
    """Paginated feed with filtering."""
    q = db.query(ResearchThread)

    if gene_symbol:
        q = q.filter(ResearchThread.gene_symbol == gene_symbol)
    if cancer_type:
        q = q.filter(ResearchThread.cancer_type == cancer_type)
    if status:
        q = q.filter(ResearchThread.status == status)

    total = q.count()

    if sort_by == "convergence":
        q = q.order_by(desc(ResearchThread.convergence_score))
    elif sort_by == "challenges":
        q = q.order_by(desc(ResearchThread.challenge_count))
    else:
        q = q.order_by(desc(ResearchThread.created_at))

    threads = q.offset((page - 1) * per_page).limit(per_page).all()
    return threads, total


def add_comment(
    db: Session,
    thread_id: int,
    author_name: str,
    body: str,
    comment_type: str = "comment",
    reply_to_comment_id: int | None = None,
    referenced_claim_ids: list[int] | None = None,
) -> HumanComment:
    """Add a comment and update denormalized count."""
    thread = db.query(ResearchThread).filter(ResearchThread.thread_id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")

    comment = HumanComment(
        thread_id=thread_id,
        author_name=author_name,
        body=body,
        comment_type=comment_type,
        reply_to_comment_id=reply_to_comment_id,
        referenced_claim_ids=referenced_claim_ids,
    )
    db.add(comment)
    thread.comment_count += 1
    db.commit()
    db.refresh(comment)
    return comment


def create_challenge(
    db: Session,
    thread_id: int,
    author_name: str,
    body: str,
    referenced_claim_ids: list[int] | None = None,
) -> HumanComment:
    """Create a challenge comment and update thread status."""
    thread = db.query(ResearchThread).filter(ResearchThread.thread_id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")

    comment = HumanComment(
        thread_id=thread_id,
        author_name=author_name,
        body=body,
        comment_type=CommentType.CHALLENGE,
        referenced_claim_ids=referenced_claim_ids,
    )
    db.add(comment)
    thread.comment_count += 1
    thread.challenge_count += 1
    if thread.status == ThreadStatus.PUBLISHED.value:
        thread.status = ThreadStatus.CHALLENGED
    db.commit()
    db.refresh(comment)
    return comment


def create_correction(
    db: Session,
    thread_id: int,
    author_name: str,
    body: str,
    referenced_claim_ids: list[int] | None = None,
) -> HumanComment:
    """Create a correction comment."""
    thread = db.query(ResearchThread).filter(ResearchThread.thread_id == thread_id).first()
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")

    comment = HumanComment(
        thread_id=thread_id,
        author_name=author_name,
        body=body,
        comment_type=CommentType.CORRECTION,
        referenced_claim_ids=referenced_claim_ids,
    )
    db.add(comment)
    thread.comment_count += 1
    db.commit()
    db.refresh(comment)
    return comment


def fork_thread(
    db: Session,
    thread_id: int,
    gene_symbol: str | None = None,
    cancer_type: str | None = None,
    modification_summary: str | None = None,
    modification_params: dict | None = None,
) -> tuple[ResearchThread, ThreadFork]:
    """Fork a thread — clone config, create new DRAFT thread."""
    parent = db.query(ResearchThread).filter(ResearchThread.thread_id == thread_id).first()
    if not parent:
        raise ValueError(f"Thread {thread_id} not found")

    child = ResearchThread(
        title=f"Fork of: {parent.title}",
        status=ThreadStatus.DRAFT,
        gene_symbol=gene_symbol or parent.gene_symbol,
        cancer_type=cancer_type or parent.cancer_type,
        forked_from_id=parent.thread_id,
        claims_snapshot=parent.claims_snapshot,
        evidence_snapshot=parent.evidence_snapshot,
    )
    db.add(child)
    db.flush()

    fork = ThreadFork(
        parent_thread_id=parent.thread_id,
        child_thread_id=child.thread_id,
        modification_summary=modification_summary,
        modification_params=modification_params or {},
    )
    db.add(fork)
    parent.fork_count += 1
    db.commit()
    db.refresh(child)
    db.refresh(fork)
    return child, fork


def search_threads(
    db: Session,
    query: str,
    gene_symbol: str | None = None,
    cancer_type: str | None = None,
) -> list[ResearchThread]:
    """Basic text search across threads."""
    q = db.query(ResearchThread).filter(
        ResearchThread.title.ilike(f"%{query}%")
        | ResearchThread.summary.ilike(f"%{query}%")
    )
    if gene_symbol:
        q = q.filter(ResearchThread.gene_symbol == gene_symbol)
    if cancer_type:
        q = q.filter(ResearchThread.cancer_type == cancer_type)
    return list(q.limit(50).all())


def watch_thread(
    db: Session,
    thread_id: int,
    watcher_name: str,
    notify_on: str = "all",
) -> ThreadWatcher:
    """Add a watcher to a thread."""
    watcher = ThreadWatcher(
        thread_id=thread_id,
        watcher_name=watcher_name,
        notify_on=notify_on,
    )
    db.add(watcher)
    db.commit()
    db.refresh(watcher)
    return watcher


def get_thread_detail(db: Session, thread_id: int) -> ResearchThread | None:
    return db.query(ResearchThread).filter(ResearchThread.thread_id == thread_id).first()
