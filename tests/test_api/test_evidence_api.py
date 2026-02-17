"""API integration tests for evidence endpoints."""

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


def test_add_evidence(test_app):
    resp = test_app.get("/api/v1/genes")
    gene_id = resp.json()[0]["gene_id"]

    resp = test_app.post(
        "/api/v1/evidence",
        json={
            "gene_id": gene_id,
            "evidence_type": "HOMOLOGY",
            "payload": {"blast_hit": "UniRef90_test", "evalue": 1e-50},
            "source_ref": "BLAST vs UniRef90",
            "confidence": 0.95,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["evidence_type"] == "HOMOLOGY"
    assert data["confidence"] == 0.95


def test_add_evidence_invalid_gene(test_app):
    resp = test_app.post(
        "/api/v1/evidence",
        json={
            "gene_id": 99999,
            "evidence_type": "HOMOLOGY",
            "payload": {},
        },
    )
    assert resp.status_code == 404
