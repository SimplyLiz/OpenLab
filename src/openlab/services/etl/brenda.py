"""BRENDA enzyme database client — async adaptation from DNAView."""

import asyncio
import hashlib
import logging

import httpx

from .disk_cache import DiskCache
from .rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)

BRENDA_WSDL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"


class AsyncBRENDAClient:
    """Async BRENDA client wrapping SOAP calls via asyncio.to_thread."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        cache: DiskCache,
        email: str = "",
        password: str = "",
        rate: float = 0.5,
    ):
        self.http = http
        self.cache = cache
        self.limiter = AsyncRateLimiter(rate)
        self.email = email
        self._password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
        self._soap_client = None
        self._soap_init_attempted = False

    def _get_soap_client(self):
        if self._soap_client is None and not self._soap_init_attempted:
            self._soap_init_attempted = True
            try:
                from zeep import Client
                self._soap_client = Client(BRENDA_WSDL)
            except Exception as e:
                logger.warning(f"BRENDA SOAP unavailable: {e}")
        return self._soap_client

    def _sync_soap_call(self, method: str, params: str) -> str:
        """Synchronous SOAP call (runs in thread pool)."""
        client = self._get_soap_client()
        if client is None:
            return ""
        try:
            result = getattr(client.service, method)(
                self.email, self._password_hash, params
            )
            return result or ""
        except Exception as e:
            logger.error(f"BRENDA SOAP error ({method}): {e}")
            return ""

    async def _soap_call(self, method: str, params: str) -> str:
        cache_key = f"brenda/{method}"
        cache_params = {"params": params}
        cached = self.cache.get(cache_key, cache_params)
        if cached is not None:
            return cached

        await self.limiter.acquire()
        result = await asyncio.to_thread(self._sync_soap_call, method, params)
        if result:
            self.cache.put(cache_key, result, cache_params)
        return result

    async def get_kcat(self, ec: str, organism: str = "Mycoplasma genitalium") -> list[dict]:
        params = f"ecNumber*{ec}#organism*{organism}#"
        raw = await self._soap_call("getTurnoverNumber", params)
        return self._parse_results(raw)

    async def get_km(self, ec: str, organism: str = "Mycoplasma genitalium") -> list[dict]:
        params = f"ecNumber*{ec}#organism*{organism}#"
        raw = await self._soap_call("getKmValue", params)
        return self._parse_results(raw)

    async def get_ki(self, ec: str, organism: str = "Mycoplasma genitalium") -> list[dict]:
        params = f"ecNumber*{ec}#organism*{organism}#"
        raw = await self._soap_call("getKiValue", params)
        return self._parse_results(raw)

    @staticmethod
    def _parse_results(raw: str) -> list[dict]:
        if not raw:
            return []
        results = []
        for entry in raw.split("!"):
            entry = entry.strip()
            if not entry:
                continue
            fields = {}
            for field in entry.split("#"):
                if "*" in field:
                    key, val = field.split("*", 1)
                    fields[key.strip()] = val.strip()
            if fields:
                results.append(fields)
        return results
