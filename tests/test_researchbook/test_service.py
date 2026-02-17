"""Tests for ResearchBook service functions."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openlab.db.models.agent import AgentRun
from openlab.db.models.base import Base
from openlab.researchbook import service
from openlab.researchbook.models import ResearchThread, ThreadStatus


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def agent_run(db):
    run = AgentRun(
        run_id="svc-run-001",
        gene_symbol="TP53",
        cancer_type="colorectal",
        status="completed",
        dossier_json={
            "claims": [{"claim_text": "TP53 is a TSG", "confidence": 0.9}],
            "provenance": [{"tool": "ncbi"}],
            "convergence_score": 0.75,
        },
    )
    db.add(run)
    db.commit()
    return run


def test_create_thread_from_agent_run(db, agent_run):
    thread = service.create_thread_from_agent_run(db, "svc-run-001")
    assert thread.thread_id is not None
    assert thread.gene_symbol == "TP53"
    assert thread.status == ThreadStatus.DRAFT.value
    assert thread.convergence_score == 0.75


def test_publish_thread(db, agent_run):
    thread = service.create_thread_from_agent_run(db, "svc-run-001")
    published = service.publish_thread(db, thread.thread_id)
    assert published.status == ThreadStatus.PUBLISHED


def test_publish_non_draft_raises(db, agent_run):
    thread = service.create_thread_from_agent_run(db, "svc-run-001")
    service.publish_thread(db, thread.thread_id)
    with pytest.raises(ValueError, match="not in DRAFT"):
        service.publish_thread(db, thread.thread_id)


def test_add_comment(db, agent_run):
    thread = service.create_thread_from_agent_run(db, "svc-run-001")
    comment = service.add_comment(db, thread.thread_id, "alice", "Good research")
    assert comment.comment_id is not None
    db.refresh(thread)
    assert thread.comment_count == 1


def test_challenge(db, agent_run):
    thread = service.create_thread_from_agent_run(db, "svc-run-001")
    service.publish_thread(db, thread.thread_id)
    comment = service.create_challenge(db, thread.thread_id, "bob", "Citation is wrong")
    assert comment.comment_type == "challenge"
    db.refresh(thread)
    assert thread.challenge_count == 1
    assert thread.status == ThreadStatus.CHALLENGED


def test_fork(db, agent_run):
    thread = service.create_thread_from_agent_run(db, "svc-run-001")
    child, fork = service.fork_thread(
        db, thread.thread_id,
        cancer_type="breast",
        modification_summary="Changed cancer type",
    )
    assert child.forked_from_id == thread.thread_id
    assert child.cancer_type == "breast"
    db.refresh(thread)
    assert thread.fork_count == 1


def test_list_feed(db, agent_run):
    for i in range(5):
        t = ResearchThread(
            title=f"Thread {i}",
            gene_symbol="TP53",
            status=ThreadStatus.PUBLISHED,
            convergence_score=i * 0.1,
        )
        db.add(t)
    db.commit()

    threads, total = service.list_feed(db, page=1, per_page=3)
    assert total == 5
    assert len(threads) == 3


def test_list_feed_filter_gene(db, agent_run):
    db.add(ResearchThread(title="A", gene_symbol="TP53", status=ThreadStatus.PUBLISHED))
    db.add(ResearchThread(title="B", gene_symbol="BRAF", status=ThreadStatus.PUBLISHED))
    db.commit()

    threads, total = service.list_feed(db, gene_symbol="BRAF")
    assert total == 1
    assert threads[0].gene_symbol == "BRAF"


def test_search(db, agent_run):
    db.add(ResearchThread(title="TP53 colorectal dossier", gene_symbol="TP53"))
    db.add(ResearchThread(title="BRAF melanoma analysis", gene_symbol="BRAF"))
    db.commit()

    results = service.search_threads(db, "melanoma")
    assert len(results) == 1
    assert results[0].gene_symbol == "BRAF"
