"""Tests for provenance ledger."""

import asyncio

import pytest

from openlab.agents.provenance import ProvenanceLedger


async def test_start_and_complete():
    ledger = ProvenanceLedger("run-1")
    call_id = await ledger.start_call("ncbi_gene_info", {"gene": "TP53"})
    assert len(call_id) == 12
    await ledger.complete_call(call_id, sources=["https://ncbi.nlm.nih.gov"], success=True)

    entries = await ledger.get_entries()
    assert len(entries) == 1
    assert entries[0].tool_name == "ncbi_gene_info"
    assert entries[0].success
    assert "https://ncbi.nlm.nih.gov" in entries[0].sources


async def test_nested_chain():
    ledger = ProvenanceLedger("run-2")
    parent_id = await ledger.start_call("retrieve_identity", {"gene": "TP53"})
    child_id = await ledger.start_call("ncbi_gene_info", {"gene": "TP53"}, parent_call_id=parent_id)
    grandchild_id = await ledger.start_call("esearch", {"db": "gene"}, parent_call_id=child_id)

    await ledger.complete_call(grandchild_id)
    await ledger.complete_call(child_id)
    await ledger.complete_call(parent_id)

    chain = await ledger.get_chain(grandchild_id)
    assert len(chain) == 3
    assert chain[0].call_id == grandchild_id
    assert chain[1].call_id == child_id
    assert chain[2].call_id == parent_id


async def test_concurrent_access():
    ledger = ProvenanceLedger("run-3")

    async def _make_call(i: int):
        cid = await ledger.start_call(f"tool_{i}", {"i": i})
        await asyncio.sleep(0.01)
        await ledger.complete_call(cid, sources=[f"source_{i}"])

    await asyncio.gather(*[_make_call(i) for i in range(20)])
    assert ledger.total_calls() == 20
    entries = await ledger.get_entries()
    assert all(e.success for e in entries)


async def test_track_context_manager():
    ledger = ProvenanceLedger("run-4")
    async with ledger.track("test_tool", {"arg": 1}) as call_id:
        assert len(call_id) == 12

    entries = await ledger.get_entries()
    assert len(entries) == 1
    assert entries[0].success


async def test_track_context_manager_error():
    ledger = ProvenanceLedger("run-5")
    with pytest.raises(ValueError, match="test error"):
        async with ledger.track("failing_tool", {}) as _call_id:
            raise ValueError("test error")

    entries = await ledger.get_entries()
    assert len(entries) == 1
    assert not entries[0].success
    assert entries[0].error == "test error"


async def test_total_duration():
    ledger = ProvenanceLedger("run-6")
    cid = await ledger.start_call("slow_tool", {})
    await asyncio.sleep(0.05)
    await ledger.complete_call(cid)

    assert ledger.total_duration_ms() >= 40  # at least ~50ms


async def test_complete_nonexistent():
    ledger = ProvenanceLedger("run-7")
    # Should not raise
    await ledger.complete_call("nonexistent", success=True)
    assert ledger.total_calls() == 0
