"""Database engine factory and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import Session, sessionmaker

from openlab.config import config

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine(config.database.url, echo=config.debug)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """Yield a database session with automatic cleanup."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
