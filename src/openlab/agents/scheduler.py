"""Agent scheduler — minimal for Phase 1, runs dossier agents."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from openlab.agents.agent_models import AgentEventType, AgentRunRecord, AgentRunStatus

logger = logging.getLogger(__name__)


class AgentScheduler:
    """Manages agent runs — single and batch."""

    def __init__(self, config: Any = None) -> None:
        self.config = config
        self._runs: dict[str, AgentRunRecord] = {}

    async def run_once(
        self, gene_symbol: str, cancer_type: str | None = None
    ) -> AgentRunRecord:
        from openlab.agents.runner import run_dossier_agent

        record = AgentRunRecord(
            gene_symbol=gene_symbol,
            cancer_type=cancer_type,
            status=AgentRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._runs[record.run_id] = record

        try:
            async for event in run_dossier_agent(gene_symbol, cancer_type):
                if event.event_type == AgentEventType.DOSSIER_COMPLETED:
                    record.status = AgentRunStatus.COMPLETED
                    record.total_tool_calls = event.data.get("total_tool_calls", 0)
                elif event.event_type == AgentEventType.RUN_FAILED:
                    record.status = AgentRunStatus.FAILED
                    record.error = event.error
        except Exception as exc:
            record.status = AgentRunStatus.FAILED
            record.error = str(exc)
        finally:
            record.completed_at = datetime.now(UTC)

        return record

    async def run_batch(
        self, genes: list[tuple[str, str | None]]
    ) -> list[AgentRunRecord]:
        results = []
        for gene_symbol, cancer_type in genes:
            record = await self.run_once(gene_symbol, cancer_type)
            results.append(record)
        return results

    def get_status(self, run_id: str) -> AgentRunRecord | None:
        return self._runs.get(run_id)

    def list_runs(self, limit: int = 20) -> list[AgentRunRecord]:
        runs = sorted(
            self._runs.values(),
            key=lambda r: r.started_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return runs[:limit]
