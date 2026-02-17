"""Tests for runner — full integration with mocked HTTP."""

import httpx

from openlab.agents.agent_models import AgentEventType
from openlab.agents.runner import run_dossier_agent


def _full_mock_handler(request: httpx.Request) -> httpx.Response:
    """Comprehensive mock that handles all tool calls."""
    url = str(request.url)

    # NCBI esearch
    if "eutils.ncbi" in url and "esearch" in url:
        return httpx.Response(200, json={"esearchresult": {"idlist": ["7157"]}})
    # NCBI esummary
    if "eutils.ncbi" in url and "esummary" in url:
        return httpx.Response(200, json={
            "result": {
                "7157": {
                    "uid": "7157",
                    "name": "TP53",
                    "description": "tumor protein p53",
                    "chromosome": "17",
                }
            }
        })
    # NCBI efetch
    if "eutils.ncbi" in url and "efetch" in url:
        return httpx.Response(200, text="<xml></xml>")
    # Ensembl
    if "ensembl.org" in url:
        return httpx.Response(200, json={
            "id": "ENSG00000141510",
            "display_name": "TP53",
            "biotype": "protein_coding",
            "seq_region_name": "17",
        })
    # UniProt
    if "uniprot.org" in url:
        return httpx.Response(200, json={
            "results": [{
                "primaryAccession": "P04637",
                "proteinDescription": {
                    "recommendedName": {
                        "fullName": {
                            "value": "Cellular tumor antigen p53",
                        },
                    },
                },
            }]
        })
    # EuropePMC
    if "europepmc" in url:
        if "EXT_ID:" in url:
            return httpx.Response(200, json={
                "resultList": {"result": [{"pmid": "12345", "title": "Valid paper"}]}
            })
        return httpx.Response(200, json={
            "resultList": {"result": [
                {
                    "pmid": "12345",
                    "title": "TP53 in cancer",
                    "authorString": "Smith J",
                    "journalTitle": "Nature",
                    "pubYear": "2024",
                    "doi": "10.1234/test",
                    "citedByCount": 100,
                }
            ]}
        })
    # Anthropic API (LLM synthesis)
    if "anthropic.com" in url:
        return httpx.Response(200, json={
            "content": [{"text": (
                "TP53 is a tumor suppressor gene [PMID:12345] (0.9). "
                "It is mutated in over 50% of human cancers [PMID:12345] (0.85). "
                "[SPECULATIVE] Novel p53-MDM4 interaction may exist (0.3)."
            )}],
            "usage": {"input_tokens": 100, "output_tokens": 200},
        })
    # Ollama
    if "localhost:11434" in url:
        if "api/tags" in url:
            return httpx.Response(200, json={"models": []})
        return httpx.Response(200, json={
            "response": (
                "TP53 is a tumor suppressor gene [PMID:12345] (0.9). "
                "[SPECULATIVE] Novel interaction (0.2)."
            )
        })

    return httpx.Response(200, json={})


async def test_runner_yields_events():
    """Verify the runner yields a sequence of expected events."""
    http = httpx.AsyncClient(transport=httpx.MockTransport(_full_mock_handler))

    event_types = []
    async for event in run_dossier_agent("TP53", "colorectal", http=http):
        event_types.append(event.event_type)
        assert event.run_id  # Every event has a run_id

    # Verify key events occurred
    assert AgentEventType.PROGRESS in event_types
    assert AgentEventType.PLAN_CREATED in event_types
    assert AgentEventType.TOOL_STARTED in event_types
    assert AgentEventType.TOOL_COMPLETED in event_types

    await http.aclose()


async def test_runner_completes_or_fails():
    """Runner should end with either DOSSIER_COMPLETED or RUN_FAILED."""
    http = httpx.AsyncClient(transport=httpx.MockTransport(_full_mock_handler))

    last_event = None
    async for event in run_dossier_agent("TP53", "colorectal", http=http):
        last_event = event

    assert last_event is not None
    assert last_event.event_type in (
        AgentEventType.DOSSIER_COMPLETED,
        AgentEventType.RUN_FAILED,
    )
    await http.aclose()


async def test_runner_without_cancer_type():
    http = httpx.AsyncClient(transport=httpx.MockTransport(_full_mock_handler))

    events = []
    async for event in run_dossier_agent("BRAF", http=http):
        events.append(event)

    assert len(events) > 0
    await http.aclose()
