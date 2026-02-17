"""Abstract base class for cancer evidence sources."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CancerEvidenceSource(ABC):
    """Base class for cancer-specific evidence sources."""

    source_name: str = ""

    @abstractmethod
    async def fetch(self, gene_symbol: str, http: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch evidence for a gene."""

    @abstractmethod
    def normalize(self, raw: dict) -> dict[str, Any]:
        """Normalize raw API response to standard evidence format."""

    async def fetch_with_retry(
        self,
        gene_symbol: str,
        http: httpx.AsyncClient,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """Fetch with exponential backoff on 429/timeout."""
        for attempt in range(max_retries):
            try:
                return await self.fetch(gene_symbol, http)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "%s: rate limited, retrying in %ds (attempt %d/%d)",
                        self.source_name, wait, attempt + 1, max_retries,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "%s: timeout/connection error, retrying in %ds",
                        self.source_name, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
        return []
