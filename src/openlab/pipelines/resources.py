"""Dagster resources: database sessions and HTTP client with retry."""

from __future__ import annotations

import time
import logging

import httpx
from dagster import ConfigurableResource
from sqlalchemy.orm import Session

from openlab.db.engine import get_session_factory

logger = logging.getLogger(__name__)


class DatabaseResource(ConfigurableResource):
    """Database session resource for Dagster assets."""

    def get_session(self) -> Session:
        factory = get_session_factory()
        return factory()


class HttpClientResource(ConfigurableResource):
    """HTTP client resource with retry, backoff, and job polling."""

    timeout: float = 60.0
    max_retries: int = 3
    backoff_factor: float = 2.0

    def get_client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout, follow_redirects=True)

    def get_with_retry(self, url: str, **kwargs) -> httpx.Response:
        """GET with exponential backoff retry."""
        client = self.get_client()
        resp = None
        for attempt in range(self.max_retries):
            try:
                resp = client.get(url, **kwargs)
                if resp.status_code < 500:
                    return resp
            except httpx.TransportError as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.debug("Retry %d for %s: %s", attempt + 1, url, e)
            time.sleep(self.backoff_factor ** attempt)
        return resp

    def poll_job(
        self,
        status_url: str,
        done_statuses: set[str] | None = None,
        error_statuses: set[str] | None = None,
        interval: float = 10.0,
        max_polls: int = 360,
    ) -> dict | None:
        """Poll a job status endpoint until completion or failure."""
        if done_statuses is None:
            done_statuses = {"DONE", "COMPLETE", "finished"}
        if error_statuses is None:
            error_statuses = {"ERROR", "FAILED"}

        client = self.get_client()
        for _ in range(max_polls):
            try:
                resp = client.get(status_url, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "")
                    if status in done_statuses:
                        return data
                    if status in error_statuses:
                        return None
            except Exception:
                pass
            time.sleep(interval)
        return None
