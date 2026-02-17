"""Base async client with disk cache and rate limiting."""

import logging

import httpx

from .disk_cache import DiskCache
from .rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)


class AsyncBaseClient:
    """Base class for async ETL API clients."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        cache: DiskCache,
        rate: float = 1.0,
    ):
        self.http = http
        self.cache = cache
        self.limiter = AsyncRateLimiter(rate)

    async def _get(
        self,
        url: str,
        params: dict | None = None,
        cache_key: str | None = None,
        timeout: float = 30.0,
    ) -> str | dict | list:
        """GET with cache check and rate limiting."""
        if cache_key:
            cached = self.cache.get(cache_key, params)
            if cached is not None:
                return cached

        await self.limiter.acquire()
        try:
            resp = await self.http.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            # Try JSON first, fall back to text
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            if cache_key:
                self.cache.put(cache_key, data, params)
            return data
        except Exception as e:
            logger.warning(f"GET {url} failed: {e}")
            return "" if isinstance(e, httpx.HTTPStatusError) else ""
