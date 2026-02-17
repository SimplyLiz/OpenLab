"""FastAPI dependencies."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from openlab.db import get_db as _get_db_gen


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session, auto-closed after request."""
    yield from _get_db_gen()


def get_http(request: Request):
    """Return the shared httpx.AsyncClient from app state."""
    return request.app.state.http
