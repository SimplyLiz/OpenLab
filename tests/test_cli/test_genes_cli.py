"""CLI integration tests."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from openlab.cli.main import app

runner = CliRunner()
FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_syn3a.gb"


def _make_test_session():
    """Create a test SessionLocal that uses SQLite."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from openlab.db.models import Base

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
    return sessionmaker(bind=engine)


@patch("openlab.cli.genes._SessionLocal")
def test_import_and_list(mock_session_local):
    TestSession = _make_test_session()
    mock_session_local.side_effect = TestSession

    # Import
    result = runner.invoke(app, ["genes", "import", str(FIXTURE)])
    assert result.exit_code == 0
    assert "imported" in result.output.lower() or "Import complete" in result.output

    # List
    result = runner.invoke(app, ["genes", "list"])
    assert result.exit_code == 0
    assert "JCVISYN3A_0001" in result.output

    # Show
    result = runner.invoke(app, ["genes", "show", "JCVISYN3A_0001"])
    assert result.exit_code == 0
    assert "dnaA" in result.output
