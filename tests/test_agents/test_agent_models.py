"""Tests for agent Pydantic models."""

from openlab.agents.agent_models import (
    AgentEvent,
    AgentEventType,
    AgentRunRecord,
    AgentRunStatus,
    CitationStatus,
    Claim,
    DossierSection,
    GeneDossier,
    ProvenanceEntry,
    ToolCall,
    ToolResult,
)


def test_agent_event_creation():
    event = AgentEvent(
        event_type=AgentEventType.PROGRESS,
        stage="test",
        data={"key": "value"},
        progress=0.5,
        run_id="abc123",
    )
    assert event.event_type == AgentEventType.PROGRESS
    assert event.stage == "test"
    assert event.progress == 0.5


def test_agent_event_round_trip():
    event = AgentEvent(
        event_type=AgentEventType.DOSSIER_COMPLETED,
        stage="complete",
        data={"claims": 5},
        run_id="xyz",
    )
    dumped = event.model_dump(mode="json")
    restored = AgentEvent.model_validate(dumped)
    assert restored.event_type == event.event_type
    assert restored.data == event.data


def test_tool_call_has_id():
    call = ToolCall(tool_name="ncbi_gene_info", arguments={"gene": "TP53"})
    assert len(call.call_id) == 12
    assert call.tool_name == "ncbi_gene_info"


def test_tool_result():
    result = ToolResult(
        call_id="abc",
        tool_name="test",
        success=True,
        data={"key": "val"},
        sources=["http://example.com"],
    )
    assert result.success
    assert result.sources == ["http://example.com"]


def test_claim_defaults():
    claim = Claim(claim_text="Test claim")
    assert claim.confidence == 0.0
    assert claim.citations == []
    assert claim.citation_status == CitationStatus.UNCHECKED
    assert not claim.is_speculative


def test_claim_with_citations():
    claim = Claim(
        claim_text="Gene X is oncogenic",
        confidence=0.9,
        citations=["PMID:12345"],
        citation_status=CitationStatus.VALID,
    )
    assert claim.confidence == 0.9
    assert len(claim.citations) == 1


def test_gene_dossier():
    dossier = GeneDossier(
        gene_symbol="TP53",
        ncbi_gene_id="7157",
        cancer_type="colorectal",
        sections=[
            DossierSection(title="Overview", content="# Overview\nTP53 is important.")
        ],
    )
    assert dossier.gene_symbol == "TP53"
    dumped = dossier.model_dump()
    assert dumped["gene_symbol"] == "TP53"
    assert len(dumped["sections"]) == 1


def test_provenance_entry():
    entry = ProvenanceEntry(
        call_id="abc",
        tool_name="ncbi_gene_info",
        duration_ms=150,
        success=True,
        sources=["https://ncbi.nlm.nih.gov"],
    )
    assert entry.duration_ms == 150
    assert entry.sources[0].startswith("https://")


def test_agent_run_record():
    record = AgentRunRecord(gene_symbol="BRAF", cancer_type="melanoma")
    assert record.status == AgentRunStatus.PENDING
    assert len(record.run_id) == 16
    assert record.gene_symbol == "BRAF"


def test_agent_event_types():
    # Verify all event types are valid
    for evt in AgentEventType:
        event = AgentEvent(event_type=evt, run_id="test")
        assert event.event_type == evt
