"""Tests for tool registry with mocked HTTP."""


import httpx

from openlab.agents.provenance import ProvenanceLedger
from openlab.agents.tools import ToolRegistry


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _europepmc_handler(request: httpx.Request) -> httpx.Response:
    """Mock EuropePMC responses."""
    url = str(request.url)
    if "europepmc" in url and "EXT_ID:" in url:
        # PMID validation
        return httpx.Response(
            200,
            json={
                "resultList": {
                    "result": [{"pmid": "12345", "title": "Test Paper"}]
                }
            },
        )
    if "europepmc" in url:
        # Literature search
        return httpx.Response(
            200,
            json={
                "resultList": {
                    "result": [
                        {
                            "pmid": "12345",
                            "title": "TP53 in cancer",
                            "authorString": "Smith J",
                            "journalTitle": "Nature",
                            "pubYear": "2024",
                            "doi": "10.1234/test",
                            "citedByCount": 100,
                        }
                    ]
                }
            },
        )
    return httpx.Response(200, json={})


async def test_unknown_tool():
    ledger = ProvenanceLedger("test-run")
    http = httpx.AsyncClient(transport=_mock_transport(lambda r: httpx.Response(200, json={})))
    tools = ToolRegistry(http, ledger)

    result = await tools.call("nonexistent_tool", {})
    assert not result.success
    assert "Unknown tool" in result.error
    await http.aclose()


async def test_available_tools():
    ledger = ProvenanceLedger("test-run")
    http = httpx.AsyncClient(transport=_mock_transport(lambda r: httpx.Response(200, json={})))
    tools = ToolRegistry(http, ledger)

    available = tools.available_tools
    assert "ncbi_gene_info" in available
    assert "cancer_literature" in available
    assert "pmid_validate" in available
    assert "llm_synthesize" in available
    await http.aclose()


async def test_cancer_literature():
    ledger = ProvenanceLedger("test-run")
    http = httpx.AsyncClient(transport=_mock_transport(_europepmc_handler))
    tools = ToolRegistry(http, ledger)

    result = await tools.call(
        "cancer_literature",
        {"gene_symbol": "TP53", "cancer_type": "colorectal"},
    )
    assert result.success
    assert len(result.data.get("articles", [])) > 0
    assert result.call_id
    assert ledger.total_calls() == 1
    await http.aclose()


async def test_pmid_validate():
    ledger = ProvenanceLedger("test-run")
    http = httpx.AsyncClient(transport=_mock_transport(_europepmc_handler))
    tools = ToolRegistry(http, ledger)

    result = await tools.call("pmid_validate", {"pmid": "12345"})
    assert result.success
    assert result.data.get("valid") is True
    assert result.data.get("pmid") == "12345"
    await http.aclose()


async def test_provenance_tracking():
    ledger = ProvenanceLedger("test-run")
    http = httpx.AsyncClient(transport=_mock_transport(_europepmc_handler))
    tools = ToolRegistry(http, ledger)

    await tools.call("cancer_literature", {"gene_symbol": "TP53"})
    await tools.call("pmid_validate", {"pmid": "12345"})

    entries = await ledger.get_entries()
    assert len(entries) == 2
    assert entries[0].tool_name == "cancer_literature"
    assert entries[1].tool_name == "pmid_validate"
    await http.aclose()


async def test_convergence_score_tool():
    ledger = ProvenanceLedger("test-run")
    http = httpx.AsyncClient(transport=_mock_transport(lambda r: httpx.Response(200, json={})))
    tools = ToolRegistry(http, ledger)

    evidence = [
        {"source": "ncbi_blast", "go_terms": ["GO:0006915"]},
        {"source": "uniprot", "go_terms": ["GO:0006915"]},
    ]
    result = await tools.call("convergence_score", {"evidence_list": evidence})
    assert result.success
    assert "convergence_score" in result.data
    await http.aclose()
