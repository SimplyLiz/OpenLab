"""Provenance ledger — append-only log of tool calls with full ancestry tracking."""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from openlab.agents.agent_models import ProvenanceEntry


class ProvenanceLedger:
    """In-memory append-only provenance log for a single agent run."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._entries: dict[str, ProvenanceEntry] = {}
        self._lock = asyncio.Lock()
        self._start_times: dict[str, float] = {}

    async def start_call(
        self,
        tool_name: str,
        arguments: dict,
        parent_call_id: str | None = None,
    ) -> str:
        call_id = uuid.uuid4().hex[:12]
        async with self._lock:
            self._entries[call_id] = ProvenanceEntry(
                call_id=call_id,
                tool_name=tool_name,
                arguments=arguments,
                started_at=datetime.now(UTC),
                parent_call_id=parent_call_id,
                success=True,
            )
            self._start_times[call_id] = time.monotonic()
        return call_id

    async def complete_call(
        self,
        call_id: str,
        sources: list[str] | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            entry = self._entries.get(call_id)
            if entry is None:
                return
            entry.completed_at = datetime.now(UTC)
            entry.success = success
            entry.error = error
            entry.sources = sources or []
            start = self._start_times.get(call_id)
            if start is not None:
                entry.duration_ms = int((time.monotonic() - start) * 1000)

    @asynccontextmanager
    async def track(self, tool_name: str, arguments: dict, parent_call_id: str | None = None):
        call_id = await self.start_call(tool_name, arguments, parent_call_id)
        try:
            yield call_id
        except Exception as exc:
            await self.complete_call(call_id, success=False, error=str(exc))
            raise
        else:
            await self.complete_call(call_id, success=True)

    async def get_entries(self) -> list[ProvenanceEntry]:
        async with self._lock:
            return list(self._entries.values())

    async def get_chain(self, call_id: str) -> list[ProvenanceEntry]:
        """Return full parent ancestry chain for a call."""
        async with self._lock:
            chain: list[ProvenanceEntry] = []
            current = call_id
            visited: set[str] = set()
            while current and current not in visited:
                visited.add(current)
                entry = self._entries.get(current)
                if entry is None:
                    break
                chain.append(entry)
                current = entry.parent_call_id
            return chain

    def total_calls(self) -> int:
        return len(self._entries)

    def total_duration_ms(self) -> int:
        return sum(e.duration_ms for e in self._entries.values())
