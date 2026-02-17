"""Tests for evidence retriever with mocked tools."""

import httpx
import pytest

from openlab.agents.provenance import ProvenanceLedger
from openlab.agents.retriever import (
    retrieve_existing_evidence,
    retrieve_gene_identity,
    retrieve_literature,
)
from openlab.agents.tools import ToolRegistry


def _mock_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "eutils.ncbi" in url and "esearch" in url:
        return httpx.Response(200, json={"esearchresult": {"idlist": ["7157"]}})
    if "eutils.ncbi" in url and "efetch" in url:
        return httpx.Response(200, text="<xml></xml>")
    if "eutils.ncbi" in url and "esummary" in url:
        return httpx.Response(200, json={
            "result": {"7157": {"uid": "7157", "name": "TP53", "description": "tumor protein p53"}}
        })
    if "ensembl.org" in url:
        return httpx.Response(200, json={"id": "ENSG00000141510", "display_name": "TP53"})
    if "uniprot.org" in url:
        return httpx.Response(200, json={"results": [{"primaryAccession": "P04637"}]})
    if "europepmc" in url:
        return httpx.Response(200, json={"resultList": {"result": [
            {"pmid": "12345", "title": "TP53 paper", "authorString": "J Smith"}
        ]}})
    return httpx.Response(200, json={})


@pytest.fixture
async def tools_with_mock():
    ledger = ProvenanceLedger("retriever-test")
    http = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
    registry = ToolRegistry(http, ledger)
    yield registry
    await http.aclose()


async def test_retrieve_gene_identity(tools_with_mock):
    identity, call_ids = await retrieve_gene_identity(tools_with_mock, "TP53")
    assert identity["gene_symbol"] == "TP53"
    assert len(call_ids) > 0


async def test_retrieve_literature(tools_with_mock):
    articles, call_ids = await retrieve_literature(tools_with_mock, "TP53", "colorectal")
    assert isinstance(articles, list)
    assert len(call_ids) > 0


async def test_retrieve_literature_no_cancer(tools_with_mock):
    articles, call_ids = await retrieve_literature(tools_with_mock, "TP53", None)
    assert isinstance(articles, list)


async def test_retrieve_existing_evidence(tools_with_mock):
    # Without gene_id, returns empty
    evidence, call_ids = await retrieve_existing_evidence(tools_with_mock, "TP53", None)
    assert isinstance(evidence, list)
