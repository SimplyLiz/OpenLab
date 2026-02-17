"""Execution loop — runs the dossier agent as an async generator of events."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from openlab.agents.agent_models import (
    AgentEvent,
    AgentEventType,
)
from openlab.agents.provenance import ProvenanceLedger
from openlab.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)


async def run_dossier_agent(
    gene_symbol: str,
    cancer_type: str | None = None,
    http: httpx.AsyncClient | None = None,
    db: Any = None,
    agent_config: Any = None,
) -> AsyncGenerator[AgentEvent, None]:
    """Run the full dossier agent pipeline, yielding events for streaming.

    Follows the orchestrator.run_pipeline() pattern exactly.
    """
    run_id = uuid.uuid4().hex[:16]
    own_http = http is None
    if own_http:
        http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    # Load config
    from openlab.config import config

    cfg = config.agent if hasattr(config, "agent") else None
    timeout = getattr(cfg, "timeout_seconds", 600)
    max_tools = getattr(cfg, "max_tool_calls", 50)
    auto_critic = getattr(cfg, "auto_critic", True)

    ledger = ProvenanceLedger(run_id)
    tools = ToolRegistry(http, ledger)

    yield AgentEvent(
        event_type=AgentEventType.PROGRESS,
        stage="init",
        data={"gene_symbol": gene_symbol, "cancer_type": cancer_type},
        progress=0.0,
        run_id=run_id,
    )

    try:
        # Phase 1: Plan
        from openlab.agents.planner import plan_gene_dossier

        plan = plan_gene_dossier(gene_symbol, cancer_type)
        yield AgentEvent(
            event_type=AgentEventType.PLAN_CREATED,
            stage="planning",
            data={"phases": len(plan.phases()), "steps": len(plan.steps)},
            progress=0.05,
            run_id=run_id,
        )

        # Phase 2: Identity retrieval (parallel)
        yield AgentEvent(
            event_type=AgentEventType.TOOL_STARTED,
            stage="identity",
            data={"tools": ["ncbi_gene_info", "ensembl_lookup", "uniprot_lookup"]},
            progress=0.1,
            run_id=run_id,
        )

        from openlab.agents.retriever import (
            retrieve_existing_evidence,
            retrieve_gene_identity,
            retrieve_literature,
        )

        identity, id_call_ids = await asyncio.wait_for(
            retrieve_gene_identity(tools, gene_symbol),
            timeout=timeout,
        )

        if not identity.get("gene_id") and not identity.get("id"):
            yield AgentEvent(
                event_type=AgentEventType.RUN_FAILED,
                stage="identity",
                error=f"Could not resolve gene identity for {gene_symbol}",
                run_id=run_id,
            )
            return

        yield AgentEvent(
            event_type=AgentEventType.TOOL_COMPLETED,
            stage="identity",
            data={"gene_symbol": gene_symbol, "sources_found": len(id_call_ids)},
            progress=0.2,
            run_id=run_id,
        )

        # Phase 3: Evidence retrieval (parallel)
        yield AgentEvent(
            event_type=AgentEventType.TOOL_STARTED,
            stage="evidence",
            data={"tools": ["literature_search", "cancer_literature", "evidence_fetch"]},
            progress=0.25,
            run_id=run_id,
        )

        gene_id = identity.get("gene_id")
        gene_id_int = int(gene_id) if gene_id and str(gene_id).isdigit() else None

        lit_task = retrieve_literature(tools, gene_symbol, cancer_type)
        ev_task = retrieve_existing_evidence(tools, gene_symbol, gene_id_int)

        (articles, lit_call_ids), (existing_evidence, ev_call_ids) = await asyncio.wait_for(
            asyncio.gather(lit_task, ev_task),
            timeout=timeout,
        )

        # Check max tool calls
        if ledger.total_calls() > max_tools:
            yield AgentEvent(
                event_type=AgentEventType.RUN_FAILED,
                stage="evidence",
                error=f"Max tool calls ({max_tools}) exceeded",
                run_id=run_id,
            )
            return

        yield AgentEvent(
            event_type=AgentEventType.TOOL_COMPLETED,
            stage="evidence",
            data={"articles": len(articles), "existing_evidence": len(existing_evidence)},
            progress=0.4,
            run_id=run_id,
        )

        # Phase 4: Convergence scoring
        all_evidence = existing_evidence + [
            {"source": "literature", "title": a.get("title", "")}
            for a in articles[:10]
        ]
        conv_result = await tools.call("convergence_score", {"evidence_list": all_evidence})
        convergence = conv_result.data.get("convergence_score", 0.0) if conv_result.success else 0.0

        # Phase 5: LLM synthesis
        yield AgentEvent(
            event_type=AgentEventType.SYNTHESIS_STARTED,
            stage="synthesis",
            data={"evidence_count": len(all_evidence)},
            progress=0.5,
            run_id=run_id,
        )

        from openlab.agents.synthesizer import synthesize_section

        sections: list[tuple[str, str, list, list[str]]] = []
        section_names = [
            "Gene Overview and Cancer Relevance",
            "Molecular Mechanisms",
            "Clinical Significance",
        ]

        for section_name in section_names:
            content, claims, syn_call_ids = await asyncio.wait_for(
                synthesize_section(
                    tools,
                    section_name,
                    identity,
                    all_evidence,
                    cancer_type,
                    prior_sections=[s[0] for s in sections],
                ),
                timeout=timeout,
            )
            sections.append((section_name, content, claims, syn_call_ids))

            for claim in claims:
                yield AgentEvent(
                    event_type=AgentEventType.CLAIM_EXTRACTED,
                    stage="synthesis",
                    data={
                        "claim": claim.claim_text[:100],
                        "confidence": claim.confidence,
                        "citations": len(claim.citations),
                    },
                    run_id=run_id,
                )

        yield AgentEvent(
            event_type=AgentEventType.SYNTHESIS_COMPLETED,
            stage="synthesis",
            data={"sections": len(sections)},
            progress=0.7,
            run_id=run_id,
        )

        # Phase 6: Critic validation
        from openlab.agents.critic import CriticReport, run_critic

        all_claims = []
        for _, _, claims, _ in sections:
            all_claims.extend(claims)

        critic_report = CriticReport()
        critic_call_ids: list[str] = []

        if auto_critic and all_claims:
            yield AgentEvent(
                event_type=AgentEventType.CRITIC_STARTED,
                stage="validation",
                data={"claims_to_check": len(all_claims)},
                progress=0.75,
                run_id=run_id,
            )

            evidence_sources = list({
                a.get("source", "unknown") for a in all_evidence
            })
            critic_report, critic_call_ids = await asyncio.wait_for(
                run_critic(tools, all_claims, evidence_sources),
                timeout=timeout,
            )

            yield AgentEvent(
                event_type=AgentEventType.CRITIC_COMPLETED,
                stage="validation",
                data={
                    "citations_valid": critic_report.citations_valid,
                    "citations_invalid": critic_report.citations_invalid,
                    "overclaiming_flags": len(critic_report.overclaiming_flags),
                },
                progress=0.85,
                run_id=run_id,
            )

        # Phase 7: Assembly
        from openlab.agents.reporter import assemble_dossier

        provenance_entries = await ledger.get_entries()

        # Split articles into general and cancer-specific
        cancer_articles = [
            a for a in articles
            if cancer_type and cancer_type.lower() in str(a).lower()
        ]
        general_articles = [a for a in articles if a not in cancer_articles]

        dossier = assemble_dossier(
            identity=identity,
            literature=general_articles,
            cancer_lit=cancer_articles,
            sections=sections,
            critic_report=critic_report,
            provenance=provenance_entries,
            convergence=convergence,
            cancer_type=cancer_type,
        )

        yield AgentEvent(
            event_type=AgentEventType.DOSSIER_COMPLETED,
            stage="complete",
            data={
                "gene_symbol": dossier.gene_symbol,
                "sections": len(dossier.sections),
                "claims": len(dossier.claims),
                "convergence_score": dossier.convergence_score,
                "total_tool_calls": ledger.total_calls(),
                "total_duration_ms": ledger.total_duration_ms(),
            },
            progress=1.0,
            run_id=run_id,
        )

    except TimeoutError:
        yield AgentEvent(
            event_type=AgentEventType.RUN_FAILED,
            stage="timeout",
            error=f"Agent run timed out after {timeout}s",
            run_id=run_id,
        )
    except Exception as exc:
        logger.exception("Agent run failed: %s", exc)
        yield AgentEvent(
            event_type=AgentEventType.RUN_FAILED,
            stage="error",
            error=str(exc),
            run_id=run_id,
        )
    finally:
        if own_http and http is not None:
            await http.aclose()
