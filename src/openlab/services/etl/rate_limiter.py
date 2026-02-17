"""Asyncio-based rate limiter for ETL clients."""

import asyncio
import time


class AsyncRateLimiter:
    """Token-bucket rate limiter for async contexts."""

    def __init__(self, rate: float = 1.0):
        """
        Args:
            rate: Maximum requests per second.
        """
        self._min_interval = 1.0 / rate if rate > 0 else 0.0
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()
