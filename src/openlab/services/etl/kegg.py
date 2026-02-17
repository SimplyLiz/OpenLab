"""KEGG REST API client — async adaptation from DNAView."""

import logging
import re

import httpx

from .async_base_client import AsyncBaseClient
from .disk_cache import DiskCache

logger = logging.getLogger(__name__)

KEGG_BASE = "https://rest.kegg.jp"


class AsyncKEGGClient(AsyncBaseClient):
    """Async client for KEGG REST API."""

    def __init__(self, http: httpx.AsyncClient, cache: DiskCache, rate: float = 3.0):
        super().__init__(http, cache, rate)

    async def get_enzyme(self, ec: str) -> str:
        data = await self._get(
            f"{KEGG_BASE}/get/ec:{ec}",
            cache_key=f"kegg/enzyme/{ec}",
        )
        return data if isinstance(data, str) else ""

    async def get_reaction(self, reaction_id: str) -> str:
        data = await self._get(
            f"{KEGG_BASE}/get/{reaction_id}",
            cache_key=f"kegg/reaction/{reaction_id}",
        )
        return data if isinstance(data, str) else ""

    async def list_pathways(self, org: str = "mge") -> list[dict]:
        data = await self._get(
            f"{KEGG_BASE}/list/pathway/{org}",
            cache_key=f"kegg/pathways/{org}",
        )
        text = data if isinstance(data, str) else ""
        pathways = []
        for line in text.strip().split("\n"):
            if "\t" in line:
                pid, name = line.split("\t", 1)
                pathways.append({"id": pid, "name": name})
        return pathways
