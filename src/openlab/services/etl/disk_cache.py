"""Simple disk-backed JSON cache — adapted from DNAView."""

import hashlib
import json
from pathlib import Path
from typing import Any


class DiskCache:
    """Thread-safe disk-backed JSON cache with SHA256 key hashing."""

    def __init__(self, cache_dir: str | Path = "data/etl_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, endpoint: str, params: dict | None = None) -> str:
        raw = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, endpoint: str, params: dict | None = None) -> Any | None:
        path = self.cache_dir / f"{self._key(endpoint, params)}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    def put(self, endpoint: str, data: Any, params: dict | None = None) -> None:
        path = self.cache_dir / f"{self._key(endpoint, params)}.json"
        path.write_text(json.dumps(data, indent=2, default=str))

    def has(self, endpoint: str, params: dict | None = None) -> bool:
        path = self.cache_dir / f"{self._key(endpoint, params)}.json"
        return path.exists()
