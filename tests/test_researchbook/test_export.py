"""Tests for RO-Crate and JSON-LD export."""

from openlab.researchbook.export import export_json_ld, export_ro_crate


def _sample_thread_data():
    return {
        "thread_id": 1,
        "title": "TP53 in colorectal cancer",
        "summary": "Comprehensive dossier",
        "gene_symbol": "TP53",
        "claims_snapshot": [
            {"claim_text": "TP53 is a tumor suppressor", "confidence": 0.95},
            {"claim_text": "Mutated in 50% of cancers", "confidence": 0.9},
        ],
        "evidence_snapshot": [{"tool": "ncbi"}, {"tool": "europepmc"}],
        "created_at": "2024-01-15T12:00:00Z",
    }


def test_ro_crate_structure():
    data = export_ro_crate(_sample_thread_data())
    assert data["@context"] == "https://w3id.org/ro/crate/1.1/context"
    assert isinstance(data["@graph"], list)
    assert len(data["@graph"]) >= 4

    # Check dataset node
    dataset = next(n for n in data["@graph"] if n.get("@type") == "Dataset")
    assert dataset["@id"] == "./"
    assert "TP53" in dataset["name"]


def test_ro_crate_claims_count():
    data = export_ro_crate(_sample_thread_data())
    claims_node = next(n for n in data["@graph"] if n.get("@id") == "#claims")
    assert claims_node["numberOfItems"] == 2


def test_json_ld_context():
    data = export_json_ld(_sample_thread_data())
    assert "@context" in data
    assert data["@type"] == "ScholarlyArticle"
    assert data["about"]["name"] == "TP53"


def test_export_empty_claims():
    data = export_ro_crate({
        "thread_id": 2,
        "title": "Empty",
        "gene_symbol": "X",
        "claims_snapshot": [],
        "evidence_snapshot": [],
    })
    claims_node = next(n for n in data["@graph"] if n.get("@id") == "#claims")
    assert claims_node["numberOfItems"] == 0
