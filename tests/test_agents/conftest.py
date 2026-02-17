"""Shared fixtures for agent tests."""

import httpx
import pytest

from openlab.agents.provenance import ProvenanceLedger
from openlab.agents.tools import ToolRegistry


@pytest.fixture
def mock_http():
    """An httpx.AsyncClient that doesn't make real requests."""
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={})
    )
    return httpx.AsyncClient(transport=transport)


@pytest.fixture
def ledger():
    return ProvenanceLedger(run_id="test-run-001")


@pytest.fixture
def tools(mock_http, ledger):
    return ToolRegistry(mock_http, ledger)


@pytest.fixture
def sample_gene_identity():
    return {
        "gene_symbol": "TP53",
        "gene_id": "7157",
        "description": "tumor protein p53",
        "chromosome": "17",
        "id": "ENSG00000141510",
        "biotype": "protein_coding",
        "seq_region_name": "17",
    }


@pytest.fixture
def sample_evidence():
    return [
        {
            "source": "ncbi_blast",
            "payload": {
                "description": "tumor protein p53",
                "go_terms": ["GO:0006915", "GO:0006281"],
            },
        },
        {
            "source": "uniprot",
            "payload": {
                "description": "cellular tumor antigen p53",
                "go_terms": ["GO:0006915", "GO:0042771"],
            },
        },
        {
            "source": "interpro",
            "payload": {
                "description": "p53 DNA-binding domain",
                "categories": ["transcription_factor"],
            },
        },
    ]


@pytest.fixture
def sample_claims():
    from openlab.agents.agent_models import Claim

    return [
        Claim(
            claim_text="TP53 is a tumor suppressor gene mutated in >50% of cancers",
            confidence=0.95,
            citations=["PMID:20301340", "PMID:17482078"],
            is_speculative=False,
        ),
        Claim(
            claim_text="Loss of p53 function leads to genomic instability",
            confidence=0.85,
            citations=["PMID:19487683"],
            is_speculative=False,
        ),
        Claim(
            claim_text="TP53 may interact with novel pathway X",
            confidence=0.3,
            citations=[],
            is_speculative=True,
        ),
    ]
