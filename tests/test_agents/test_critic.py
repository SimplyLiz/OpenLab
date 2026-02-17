"""Tests for critic validation."""

import httpx
import pytest

from openlab.agents.agent_models import CitationStatus, Claim
from openlab.agents.critic import (
    CriticReport,
    detect_circular_reasoning,
    detect_overclaiming,
    run_critic,
    validate_citations,
)
from openlab.agents.provenance import ProvenanceLedger
from openlab.agents.tools import ToolRegistry


def _europepmc_handler(request: httpx.Request) -> httpx.Response:
    query = dict(request.url.params).get("query", "")
    if "EXT_ID:12345" in query or "EXT_ID:20301340" in query:
        return httpx.Response(
            200,
            json={"resultList": {"result": [{"pmid": "12345", "title": "Valid paper"}]}},
        )
    if "EXT_ID:99999" in query:
        return httpx.Response(200, json={"resultList": {"result": []}})
    return httpx.Response(200, json={"resultList": {"result": []}})


@pytest.fixture
async def critic_tools():
    ledger = ProvenanceLedger("critic-test")
    http = httpx.AsyncClient(transport=httpx.MockTransport(_europepmc_handler))
    tools = ToolRegistry(http, ledger)
    yield tools
    await http.aclose()


async def test_validate_valid_citations(critic_tools):
    claims = [
        Claim(
            claim_text="TP53 is a tumor suppressor",
            confidence=0.9,
            citations=["PMID:12345"],
        )
    ]
    validated, call_ids = await validate_citations(critic_tools, claims)
    assert len(validated) == 1
    assert validated[0].citation_status == CitationStatus.VALID


async def test_validate_invalid_citations(critic_tools):
    claims = [
        Claim(
            claim_text="Fake claim",
            confidence=0.8,
            citations=["PMID:99999"],
        )
    ]
    validated, call_ids = await validate_citations(critic_tools, claims)
    assert len(validated) == 1
    assert validated[0].citation_status == CitationStatus.INVALID


async def test_no_citations_stays_unchecked(critic_tools):
    claims = [Claim(claim_text="Speculative claim without citations")]
    validated, _ = await validate_citations(critic_tools, claims)
    assert validated[0].citation_status == CitationStatus.UNCHECKED
    assert validated[0].is_speculative
    assert validated[0].confidence == 0.0


def test_detect_overclaiming():
    claims = [
        Claim(claim_text="High confidence claim", confidence=0.9, citations=["PMID:12345"]),
        Claim(claim_text="Another high confidence", confidence=0.8, citations=[]),
    ]
    flags = detect_overclaiming(claims, evidence_count=2)
    assert len(flags) >= 1
    assert "Overclaiming" in flags[0]


def test_detect_overclaiming_few_sources():
    claims = [Claim(claim_text="Very confident", confidence=0.9, citations=["PMID:12345"])]
    flags = detect_overclaiming(claims, evidence_count=1)
    assert any("evidence sources" in f for f in flags)


def test_detect_circular_reasoning():
    claims = [
        Claim(
            claim_text="Circular claim",
            confidence=0.5,
            citations=["llm_synthesis_output"],
        )
    ]
    flags = detect_circular_reasoning(claims, [])
    assert len(flags) >= 1
    assert "Circular reasoning" in flags[0]


def test_no_circular_reasoning():
    claims = [
        Claim(claim_text="Real claim", confidence=0.8, citations=["PMID:12345"])
    ]
    flags = detect_circular_reasoning(claims, [])
    assert len(flags) == 0


async def test_full_critic(critic_tools):
    claims = [
        Claim(
            claim_text="TP53 loss leads to cancer progression",
            confidence=0.9,
            citations=["PMID:12345"],
        ),
        Claim(
            claim_text="Unfounded speculation",
            confidence=0.5,
            citations=[],
        ),
    ]
    report, call_ids = await run_critic(critic_tools, claims, ["ncbi_blast", "literature"])
    assert report.claims_checked == 2
    assert isinstance(report, CriticReport)
