"""Tests for ResearchBook API endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import all models to register them with Base.metadata
from openlab.db.models import AgentRun, Base
from openlab.researchbook.models import ResearchThread, ThreadStatus

# Shared engine for all tests — StaticPool ensures same connection across threads
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_engine)
_SessionLocal = sessionmaker(bind=_engine)


def _get_test_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_test_app() -> FastAPI:
    """Build a minimal FastAPI app with just the researchbook router."""
    from openlab.db import get_db
    from openlab.researchbook.api import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _get_test_db
    return app


@pytest.fixture(autouse=True)
def _seed_data():
    """Reset and seed the DB before each test."""
    # Clean tables
    with _SessionLocal() as db:
        db.query(ResearchThread).delete()
        db.query(AgentRun).delete()
        db.commit()

        # Seed agent run
        run = AgentRun(
            run_id="api-run-001",
            gene_symbol="TP53",
            cancer_type="colorectal",
            status="completed",
            dossier_json={"claims": [], "convergence_score": 0.5},
        )
        db.add(run)
        db.commit()


@pytest.fixture
def client():
    app = _build_test_app()
    return TestClient(app)


def test_create_thread(client):
    resp = client.post("/api/v1/researchbook/threads", json={
        "agent_run_id": "api-run-001",
        "title": "TP53 Research",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "thread_id" in data
    assert data["status"] == "draft"


def test_publish_thread(client):
    resp = client.post("/api/v1/researchbook/threads", json={
        "agent_run_id": "api-run-001",
    })
    thread_id = resp.json()["thread_id"]

    resp = client.patch(f"/api/v1/researchbook/threads/{thread_id}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


def test_add_comment(client):
    resp = client.post("/api/v1/researchbook/threads", json={"agent_run_id": "api-run-001"})
    thread_id = resp.json()["thread_id"]

    resp = client.post(f"/api/v1/researchbook/threads/{thread_id}/comments", json={
        "author_name": "alice",
        "body": "Great analysis!",
    })
    assert resp.status_code == 200
    assert "comment_id" in resp.json()


def test_challenge_thread(client):
    resp = client.post("/api/v1/researchbook/threads", json={"agent_run_id": "api-run-001"})
    thread_id = resp.json()["thread_id"]
    client.patch(f"/api/v1/researchbook/threads/{thread_id}/publish")

    resp = client.post(f"/api/v1/researchbook/threads/{thread_id}/challenge", json={
        "author_name": "bob",
        "body": "This citation doesn't support the claim",
    })
    assert resp.status_code == 200
    assert resp.json()["challenge"] is True


def test_fork_thread(client):
    resp = client.post("/api/v1/researchbook/threads", json={"agent_run_id": "api-run-001"})
    thread_id = resp.json()["thread_id"]

    resp = client.post(f"/api/v1/researchbook/threads/{thread_id}/fork", json={
        "cancer_type": "breast",
        "modification_summary": "Testing breast cancer",
    })
    assert resp.status_code == 200
    assert "child_thread_id" in resp.json()


def test_get_feed(client):
    with _SessionLocal() as db:
        for i in range(3):
            db.add(ResearchThread(
                title=f"Thread {i}",
                gene_symbol="TP53",
                status=ThreadStatus.PUBLISHED,
            ))
        db.commit()

    resp = client.get("/api/v1/researchbook/feed")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_search(client):
    with _SessionLocal() as db:
        db.add(ResearchThread(title="TP53 colorectal", gene_symbol="TP53"))
        db.commit()

    resp = client.get("/api/v1/researchbook/search?query=colorectal")
    assert resp.status_code == 200


def test_export_json(client):
    with _SessionLocal() as db:
        db.add(ResearchThread(
            title="Export test",
            gene_symbol="TP53",
            claims_snapshot=[{"claim_text": "test", "confidence": 0.5}],
        ))
        db.commit()

    # Get the thread id
    with _SessionLocal() as db:
        thread = db.query(ResearchThread).filter(ResearchThread.title == "Export test").first()
        thread_id = thread.thread_id

    resp = client.get(f"/api/v1/researchbook/threads/{thread_id}/export?format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert "@context" in data
