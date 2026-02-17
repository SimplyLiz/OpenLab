"""ResearchBook API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from openlab.db import get_db
from openlab.researchbook import export, notifications, service
from openlab.researchbook.schemas import (
    ChallengeCreate,
    CommentCreate,
    CorrectionCreate,
    ForkCreate,
    ThreadCreate,
    ThreadListItem,
)

router = APIRouter(prefix="/researchbook", tags=["researchbook"])


@router.get("/feed", response_model=list[ThreadListItem])
def get_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    gene_symbol: str | None = None,
    cancer_type: str | None = None,
    status: str | None = None,
    sort_by: str = Query(
        "recent",
        pattern="^(recent|convergence|challenges)$",
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Paginated research feed with filters."""
    threads, total = service.list_feed(
        db, page=page, per_page=per_page,
        gene_symbol=gene_symbol, cancer_type=cancer_type,
        status=status, sort_by=sort_by,
    )
    return [
        ThreadListItem(
            thread_id=t.thread_id,
            title=t.title,
            summary=t.summary,
            status=(
                t.status
                if isinstance(t.status, str)
                else t.status.value
            ),
            gene_symbol=t.gene_symbol,
            cancer_type=t.cancer_type,
            convergence_score=t.convergence_score,
            confidence_tier=t.confidence_tier,
            comment_count=t.comment_count,
            challenge_count=t.challenge_count,
            fork_count=t.fork_count,
            created_at=t.created_at,
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}")
def get_thread(
    thread_id: int,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Full thread detail with comments and forks."""
    thread = service.get_thread_detail(db, thread_id)
    if not thread:
        return {"error": "Thread not found"}
    return {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "summary": thread.summary,
        "status": (
            thread.status
            if isinstance(thread.status, str)
            else thread.status.value
        ),
        "gene_symbol": thread.gene_symbol,
        "cancer_type": thread.cancer_type,
        "convergence_score": thread.convergence_score,
        "claims_snapshot": thread.claims_snapshot,
        "evidence_snapshot": thread.evidence_snapshot,
        "comment_count": thread.comment_count,
        "challenge_count": thread.challenge_count,
        "fork_count": thread.fork_count,
        "comments": [
            {
                "comment_id": c.comment_id,
                "author_name": c.author_name,
                "body": c.body,
                "comment_type": (
                    c.comment_type
                    if isinstance(c.comment_type, str)
                    else c.comment_type.value
                ),
                "reply_to_comment_id": c.reply_to_comment_id,
                "created_at": (
                    str(c.created_at) if c.created_at else None
                ),
            }
            for c in thread.comments
        ],
    }


@router.post("/threads")
def create_thread(
    request: ThreadCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a thread from an agent run."""
    thread = service.create_thread_from_agent_run(
        db, request.agent_run_id, request.title,
        request.gene_symbol, request.cancer_type,
    )
    status = (
        thread.status
        if isinstance(thread.status, str)
        else thread.status.value
    )
    return {"thread_id": thread.thread_id, "status": status}


@router.patch("/threads/{thread_id}/publish")
def publish_thread(
    thread_id: int,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Publish a draft thread."""
    thread = service.publish_thread(db, thread_id)
    status = (
        thread.status
        if isinstance(thread.status, str)
        else thread.status.value
    )
    return {"thread_id": thread.thread_id, "status": status}


@router.post("/threads/{thread_id}/comments")
def add_comment(
    thread_id: int,
    request: CommentCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Add a comment to a thread."""
    comment = service.add_comment(
        db, thread_id, request.author_name, request.body,
        request.comment_type, request.reply_to_comment_id,
        request.referenced_claim_ids,
    )
    return {"comment_id": comment.comment_id}


@router.post("/threads/{thread_id}/challenge")
def challenge_thread(
    thread_id: int,
    request: ChallengeCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Challenge claims in a thread."""
    comment = service.create_challenge(
        db, thread_id, request.author_name, request.body,
        request.referenced_claim_ids,
    )
    return {"comment_id": comment.comment_id, "challenge": True}


@router.post("/threads/{thread_id}/correct")
def correct_thread(
    thread_id: int,
    request: CorrectionCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Submit a correction to a thread."""
    comment = service.create_correction(
        db, thread_id, request.author_name, request.body,
        request.referenced_claim_ids,
    )
    return {"comment_id": comment.comment_id, "correction": True}


@router.post("/threads/{thread_id}/fork")
def fork_thread(
    thread_id: int,
    request: ForkCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Fork a thread with modifications."""
    child, fork_record = service.fork_thread(
        db, thread_id, request.gene_symbol, request.cancer_type,
        request.modification_summary, request.modification_params,
    )
    return {
        "fork_id": fork_record.fork_id,
        "child_thread_id": child.thread_id,
    }


@router.get("/search")
def search(
    query: str = Query(..., min_length=2),
    gene_symbol: str | None = None,
    cancer_type: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Search threads."""
    threads = service.search_threads(
        db, query, gene_symbol, cancer_type,
    )
    return [
        {
            "thread_id": t.thread_id,
            "title": t.title,
            "gene_symbol": t.gene_symbol,
        }
        for t in threads
    ]


@router.get("/threads/{thread_id}/export")
def export_thread(
    thread_id: int,
    format: str = Query(
        "json", pattern="^(ro-crate|json)$",
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Export a thread as RO-Crate or JSON-LD."""
    thread = service.get_thread_detail(db, thread_id)
    if not thread:
        return {"error": "Thread not found"}

    data = {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "summary": thread.summary,
        "gene_symbol": thread.gene_symbol,
        "claims_snapshot": thread.claims_snapshot,
        "evidence_snapshot": thread.evidence_snapshot,
        "created_at": (
            str(thread.created_at) if thread.created_at else ""
        ),
    }

    if format == "ro-crate":
        return export.export_ro_crate(data)
    return export.export_json_ld(data)


@router.post("/threads/{thread_id}/watch")
def watch_thread(
    thread_id: int,
    watcher_name: str = Query(...),
    notify_on: str = Query("all"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Watch a thread for updates."""
    watcher = service.watch_thread(
        db, thread_id, watcher_name, notify_on,
    )
    return {"watcher_id": watcher.id}


@router.get("/notifications/{watcher_name}")
def get_notifications(
    watcher_name: str,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Get pending notifications."""
    return notifications.get_notifications(db, watcher_name)
