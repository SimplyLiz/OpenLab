"""Tests for ResearchBook DB models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from openlab.db.models.agent import AgentRun
from openlab.db.models.base import Base
from openlab.researchbook.models import (
    CommentType,
    HumanComment,
    ResearchThread,
    ThreadFork,
    ThreadStatus,
    ThreadWatcher,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _make_agent_run(db: Session) -> AgentRun:
    run = AgentRun(
        run_id="test-run-001",
        gene_symbol="TP53",
        cancer_type="colorectal",
        status="completed",
    )
    db.add(run)
    db.commit()
    return run


def test_create_thread(db):
    _make_agent_run(db)
    thread = ResearchThread(
        title="TP53 Dossier",
        gene_symbol="TP53",
        cancer_type="colorectal",
        agent_run_id="test-run-001",
        status=ThreadStatus.DRAFT,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)

    assert thread.thread_id is not None
    assert thread.status == ThreadStatus.DRAFT


def test_publish_thread(db):
    thread = ResearchThread(
        title="Test Thread",
        gene_symbol="BRAF",
        status=ThreadStatus.DRAFT,
    )
    db.add(thread)
    db.commit()

    thread.status = ThreadStatus.PUBLISHED
    db.commit()
    db.refresh(thread)
    assert thread.status == ThreadStatus.PUBLISHED


def test_add_comment(db):
    thread = ResearchThread(title="Test", gene_symbol="TP53", status=ThreadStatus.PUBLISHED)
    db.add(thread)
    db.commit()

    comment = HumanComment(
        thread_id=thread.thread_id,
        author_name="researcher",
        body="Great analysis!",
        comment_type=CommentType.COMMENT,
    )
    db.add(comment)
    db.commit()

    assert len(thread.comments) == 1
    assert thread.comments[0].body == "Great analysis!"


def test_fork_lineage(db):
    parent = ResearchThread(title="Parent", gene_symbol="TP53")
    db.add(parent)
    db.commit()

    child = ResearchThread(
        title="Child Fork",
        gene_symbol="TP53",
        cancer_type="breast",
        forked_from_id=parent.thread_id,
    )
    db.add(child)
    db.commit()

    fork = ThreadFork(
        parent_thread_id=parent.thread_id,
        child_thread_id=child.thread_id,
        modification_summary="Changed cancer type to breast",
    )
    db.add(fork)
    db.commit()

    assert child.forked_from_id == parent.thread_id
    assert len(parent.child_forks) == 1


def test_cascade_delete(db):
    thread = ResearchThread(title="Test", gene_symbol="BRAF")
    db.add(thread)
    db.commit()

    comment = HumanComment(
        thread_id=thread.thread_id,
        author_name="user",
        body="Test comment",
    )
    db.add(comment)
    db.commit()

    watcher = ThreadWatcher(
        thread_id=thread.thread_id,
        watcher_name="user1",
    )
    db.add(watcher)
    db.commit()

    db.delete(thread)
    db.commit()

    assert db.query(HumanComment).count() == 0
    assert db.query(ThreadWatcher).count() == 0
