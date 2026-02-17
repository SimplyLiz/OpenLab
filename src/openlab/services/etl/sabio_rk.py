"""SABIO-RK kinetics database client — async adaptation from DNAView."""

import logging
import xml.etree.ElementTree as ET

import httpx

from .async_base_client import AsyncBaseClient
from .disk_cache import DiskCache

logger = logging.getLogger(__name__)

SABIO_BASE = "http://sabiork.h-its.org/sabioRestWebServices"


class AsyncSabioRKClient(AsyncBaseClient):
    """Async client for SABIO-RK kinetics database."""

    def __init__(self, http: httpx.AsyncClient, cache: DiskCache, rate: float = 1.0):
        super().__init__(http, cache, rate)

    async def search_kinetics(
        self,
        ec: str,
        organism: str = "Mycoplasma genitalium",
    ) -> list[dict]:
        query = f'ECNumber:"{ec}" AND Organism:"{organism}"' if organism else f'ECNumber:"{ec}"'
        cache_key = f"sabio/search/{ec}/{organism}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        await self.limiter.acquire()
        try:
            resp = await self.http.get(
                f"{SABIO_BASE}/searchKineticLaws/sbml",
                params={"q": query},
                timeout=30,
            )
            if resp.status_code == 200:
                entries = self._parse_sbml(resp.text, ec)
                self.cache.put(cache_key, entries)
                return entries
            else:
                logger.warning(f"SABIO-RK returned {resp.status_code} for EC {ec}")
                return []
        except Exception as e:
            logger.error(f"SABIO-RK error for EC {ec}: {e}")
            return []

    async def search_kinetics_broad(self, ec: str) -> list[dict]:
        return await self.search_kinetics(ec, organism="")

    @staticmethod
    def _parse_sbml(sbml_text: str, ec: str) -> list[dict]:
        entries = []
        try:
            root = ET.fromstring(sbml_text)
            ns = {"sbml": "http://www.sbml.org/sbml/level2/version4"}
            for reaction in root.findall(".//sbml:reaction", ns):
                entry = {
                    "ecNumber": ec,
                    "reactionId": reaction.get("id", ""),
                    "name": reaction.get("name", ""),
                    "parameters": {},
                }
                for param in reaction.findall(".//sbml:parameter", ns):
                    pid = param.get("id", "")
                    pname = param.get("name", pid)
                    value = param.get("value")
                    if value:
                        try:
                            entry["parameters"][pname] = float(value)
                        except ValueError:
                            pass
                if entry["parameters"]:
                    entries.append(entry)
        except ET.ParseError as e:
            logger.warning(f"Failed to parse SABIO-RK SBML: {e}")
        return entries
