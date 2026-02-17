"""API integration tests for hypothesis endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from openlab.api.app import create_app
from openlab.api.deps import get_db
from openlab.db.models import Base, Evidence, EvidenceType, Gene, Hypothesis, HypothesisEvidence
from openlab.db.models.hypothesis import EvidenceDirection, HypothesisScope, HypothesisStatus
from openlab.services.import_service import import_genbank

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_syn3a.gb"


@pytest.fixture(scope="module")
def test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    # Seed data
    db = TestSession()
    import_genbank(db, FIXTURE)

    # Add evidence and hypothesis
    gene = db.query(Gene).first()
    ev = Evidence(
        gene_id=gene.gene_id,
        evidence_type=EvidenceType.HOMOLOGY,
        payload={"source": "BLAST", "hits": [{"accession": "P12345"}]},
        confidence=0.8,
    )
    db.add(ev)
    db.flush()

    hyp = Hypothesis(
        title="Test hypothesis for gene",
        description="Based on BLAST homology to P12345",
        scope=HypothesisScope.GENE,
        status=HypothesisStatus.DRAFT,
        confidence_score=0.75,
        gene_id=gene.gene_id,
    )
    db.add(hyp)
    db.flush()

    link = HypothesisEvidence(
        hypothesis_id=hyp.hypothesis_id,
        evidence_id=ev.evidence_id,
        direction=EvidenceDirection.SUPPORTS,
        weight=1.0,
    )
    db.add(link)
    db.commit()
    db.close()

    app = create_app()

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

    Base.metadata.drop_all(engine)


def test_list_hypotheses(test_app):
    resp = test_app.get("/api/v1/hypotheses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Test hypothesis for gene"
    assert data[0]["confidence_score"] == 0.75
    assert data[0]["gene_id"] is not None


def test_list_hypotheses_filter_gene_id(test_app):
    # Get the gene_id from the seeded data
    genes_resp = test_app.get("/api/v1/genes")
    gene_id = genes_resp.json()[0]["gene_id"]

    resp = test_app.get(f"/api/v1/hypotheses?gene_id={gene_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(h["gene_id"] == gene_id for h in data)


def test_get_hypothesis(test_app):
    resp = test_app.get("/api/v1/hypotheses")
    hyp_id = resp.json()[0]["hypothesis_id"]

    resp = test_app.get(f"/api/v1/hypotheses/{hyp_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Based on BLAST homology to P12345"
    assert len(data["evidence_links"]) == 1


def test_get_hypothesis_not_found(test_app):
    resp = test_app.get("/api/v1/hypotheses/99999")
    assert resp.status_code == 404


def test_create_hypothesis(test_app):
    resp = test_app.post(
        "/api/v1/hypotheses",
        json={"title": "New hypothesis", "description": "Test create"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New hypothesis"
    assert data["status"] == "DRAFT"
    assert data["scope"] == "GENE"


def test_create_hypothesis_with_gene_id(test_app):
    genes_resp = test_app.get("/api/v1/genes")
    gene_id = genes_resp.json()[0]["gene_id"]

    resp = test_app.post(
        "/api/v1/hypotheses",
        json={"title": "Gene-linked hyp", "gene_id": gene_id},
    )
    assert resp.status_code == 201
    assert resp.json()["gene_id"] == gene_id


def test_update_hypothesis(test_app):
    # Create then update
    create_resp = test_app.post(
        "/api/v1/hypotheses",
        json={"title": "To update"},
    )
    hyp_id = create_resp.json()["hypothesis_id"]

    resp = test_app.patch(
        f"/api/v1/hypotheses/{hyp_id}",
        json={"title": "Updated title", "status": "TESTING"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated title"
    assert resp.json()["status"] == "TESTING"


def test_update_hypothesis_not_found(test_app):
    resp = test_app.patch(
        "/api/v1/hypotheses/99999",
        json={"title": "Nope"},
    )
    assert resp.status_code == 404


def test_delete_hypothesis(test_app):
    create_resp = test_app.post(
        "/api/v1/hypotheses",
        json={"title": "To delete"},
    )
    hyp_id = create_resp.json()["hypothesis_id"]

    resp = test_app.delete(f"/api/v1/hypotheses/{hyp_id}")
    assert resp.status_code == 204

    # Confirm gone
    resp = test_app.get(f"/api/v1/hypotheses/{hyp_id}")
    assert resp.status_code == 404


def test_delete_hypothesis_not_found(test_app):
    resp = test_app.delete("/api/v1/hypotheses/99999")
    assert resp.status_code == 404


def test_link_evidence(test_app):
    # Get an existing evidence id
    genes_resp = test_app.get("/api/v1/genes")
    gene_id = genes_resp.json()[0]["gene_id"]
    gene_resp = test_app.get(f"/api/v1/genes/{gene_id}")
    ev_id = gene_resp.json()["evidence"][0]["evidence_id"]

    # Create hypothesis
    create_resp = test_app.post(
        "/api/v1/hypotheses",
        json={"title": "Link test"},
    )
    hyp_id = create_resp.json()["hypothesis_id"]

    resp = test_app.post(
        f"/api/v1/hypotheses/{hyp_id}/evidence",
        json={"evidence_id": ev_id, "direction": "SUPPORTS", "weight": 2.0},
    )
    assert resp.status_code == 201
    assert resp.json()["evidence_id"] == ev_id
    assert resp.json()["direction"] == "SUPPORTS"
    assert resp.json()["weight"] == 2.0


def test_unlink_evidence(test_app):
    genes_resp = test_app.get("/api/v1/genes")
    gene_id = genes_resp.json()[0]["gene_id"]
    gene_resp = test_app.get(f"/api/v1/genes/{gene_id}")
    ev_id = gene_resp.json()["evidence"][0]["evidence_id"]

    create_resp = test_app.post(
        "/api/v1/hypotheses",
        json={"title": "Unlink test"},
    )
    hyp_id = create_resp.json()["hypothesis_id"]

    # Link first
    test_app.post(
        f"/api/v1/hypotheses/{hyp_id}/evidence",
        json={"evidence_id": ev_id, "direction": "SUPPORTS", "weight": 1.0},
    )

    # Unlink
    resp = test_app.delete(f"/api/v1/hypotheses/{hyp_id}/evidence/{ev_id}")
    assert resp.status_code == 204


def test_compute_score(test_app):
    resp = test_app.get("/api/v1/hypotheses")
    hyp_id = resp.json()[0]["hypothesis_id"]

    resp = test_app.post(f"/api/v1/hypotheses/{hyp_id}/score")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hypothesis_id"] == hyp_id
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_compute_score_not_found(test_app):
    resp = test_app.post("/api/v1/hypotheses/99999/score")
    assert resp.status_code == 404


def test_gene_hypothesis_endpoint(test_app):
    genes_resp = test_app.get("/api/v1/genes")
    gene_id = genes_resp.json()[0]["gene_id"]

    resp = test_app.get(f"/api/v1/genes/{gene_id}/hypothesis")
    assert resp.status_code == 200
    data = resp.json()
    assert "title" in data
    assert data["hypothesis_id"] is not None


def test_gene_hypothesis_not_found(test_app):
    resp = test_app.get("/api/v1/genes/99999/hypothesis")
    assert resp.status_code == 404
