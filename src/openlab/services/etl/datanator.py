"""Datanator API client — async adaptation from DNAView."""

import logging

import httpx

from .async_base_client import AsyncBaseClient
from .disk_cache import DiskCache

logger = logging.getLogger(__name__)

DATANATOR_BASE = "https://datanator.info/api"


class AsyncDatanatorClient(AsyncBaseClient):
    """Async client for Datanator REST API."""

    def __init__(self, http: httpx.AsyncClient, cache: DiskCache, rate: float = 1.0):
        super().__init__(http, cache, rate)

    async def get_rate_constants(self, ec: str, taxid: int = 243273) -> list[dict]:
        try:
            data = await self._get(
                f"{DATANATOR_BASE}/reactions/kinlaw/",
                params={"ec": ec, "taxon_id": taxid},
                cache_key=f"datanator/kinlaw/{ec}/{taxid}",
            )
            if isinstance(data, list):
                return data
            return data.get("results", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.warning(f"Datanator rate constant lookup failed for EC {ec}: {e}")
            return []

    async def get_metabolite_conc(self, metabolite: str, taxid: int = 243273) -> list[dict]:
        try:
            data = await self._get(
                f"{DATANATOR_BASE}/metabolites/concentration/",
                params={"metabolite": metabolite, "taxon_id": taxid},
                cache_key=f"datanator/conc/{metabolite}/{taxid}",
            )
            if isinstance(data, list):
                return data
            return data.get("results", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.warning(f"Datanator concentration lookup failed for {metabolite}: {e}")
            return []
