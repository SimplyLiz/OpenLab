"""API integration tests for gene endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from openlab.api.app import create_app
from openlab.api.deps import get_db
from openlab.db.models import Base
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


def test_list_genes(test_app):
    resp = test_app.get("/api/v1/genes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4


def test_list_genes_unknown_only(test_app):
    resp = test_app.get("/api/v1/genes?unknown_only=true")
    assert resp.status_code == 200
    data = resp.json()
    tags = [g["locus_tag"] for g in data]
    assert "JCVISYN3A_0002" in tags
    assert "JCVISYN3A_0001" not in tags


def test_get_gene(test_app):
    resp = test_app.get("/api/v1/genes")
    gene_id = resp.json()[0]["gene_id"]

    resp = test_app.get(f"/api/v1/genes/{gene_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "sequence" in data
    assert "features" in data
    assert "evidence" in data


def test_get_gene_not_found(test_app):
    resp = test_app.get("/api/v1/genes/99999")
    assert resp.status_code == 404


def test_get_dossier(test_app):
    resp = test_app.get("/api/v1/genes")
    gene_id = resp.json()[0]["gene_id"]

    resp = test_app.get(f"/api/v1/genes/{gene_id}/dossier")
    assert resp.status_code == 200
    data = resp.json()
    assert "evidence_by_type" in data
    assert "evidence_count" in data


# ── Graduation endpoints ─────────────────────────────────────────────

def _get_unknown_gene_id(test_app):
    """Get an unknown-function gene ID for graduation tests."""
    resp = test_app.get("/api/v1/genes?unknown_only=true")
    data = resp.json()
    assert len(data) > 0
    return data[0]["gene_id"]


def test_graduate_gene(test_app):
    gene_id = _get_unknown_gene_id(test_app)
    resp = test_app.patch(
        f"/api/v1/genes/{gene_id}/graduate",
        json={"proposed_function": "membrane transporter"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["proposed_function"] == "membrane transporter"
    assert data["graduated_at"] is not None


def test_graduate_gene_not_found(test_app):
    resp = test_app.patch(
        "/api/v1/genes/99999/graduate",
        json={"proposed_function": "something"},
    )
    assert resp.status_code == 404


def test_ungraduate_gene(test_app):
    # Use a different unknown gene (JCVISYN3A_0003 or _0004) — graduate then ungraduate
    resp = test_app.get("/api/v1/genes")
    all_genes = resp.json()
    # Find an ungraduated unknown gene (product contains "hypothetical")
    target = None
    for g in all_genes:
        if g.get("product") and "hypothetical" in g["product"].lower() and g.get("graduated_at") is None:
            target = g
            break
    # If all hypotheticals are already graduated from previous test, use the one from test_graduate_gene
    if target is None:
        # Fall back: find any gene that was graduated (from test_graduate_gene)
        for g in all_genes:
            if g.get("graduated_at") is not None:
                target = g
                break
    assert target is not None
    gene_id = target["gene_id"]

    # Ensure it's graduated
    test_app.patch(
        f"/api/v1/genes/{gene_id}/graduate",
        json={"proposed_function": "test function"},
    )
    resp = test_app.delete(f"/api/v1/genes/{gene_id}/graduate")
    assert resp.status_code == 204


def test_ungraduate_not_graduated(test_app):
    # dnaA (known function) is not graduated
    resp = test_app.get("/api/v1/genes")
    gene_id = resp.json()[0]["gene_id"]
    resp = test_app.delete(f"/api/v1/genes/{gene_id}/graduate")
    assert resp.status_code == 409
