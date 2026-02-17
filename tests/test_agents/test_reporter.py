"""Tests for dossier assembly and rendering."""

from openlab.agents.agent_models import Claim, ProvenanceEntry
from openlab.agents.critic import CriticReport
from openlab.agents.reporter import assemble_dossier, render_json, render_markdown


def _make_identity():
    return {
        "gene_symbol": "TP53",
        "gene_id": "7157",
        "id": "ENSG00000141510",
        "chromosome": "17",
        "description": "tumor protein p53",
    }


def _make_claims():
    return [
        Claim(
            claim_text="TP53 is mutated in >50% of cancers",
            confidence=0.95,
            citations=["PMID:20301340"],
        ),
        Claim(
            claim_text="p53 induces apoptosis",
            confidence=0.9,
            citations=["PMID:17482078"],
        ),
    ]


def _make_provenance():
    return [
        ProvenanceEntry(
            call_id="abc",
            tool_name="ncbi_gene_info",
            duration_ms=150,
            success=True,
            sources=["https://ncbi.nlm.nih.gov/gene/7157"],
        ),
        ProvenanceEntry(
            call_id="def",
            tool_name="cancer_literature",
            duration_ms=300,
            success=True,
            sources=["https://europepmc.org"],
        ),
    ]


def test_assemble_dossier():
    identity = _make_identity()
    claims = _make_claims()
    sections = [("Overview", "# Overview\nTP53 overview.", claims, ["abc"])]
    critic = CriticReport(claims_checked=2, revised_claims=claims)

    dossier = assemble_dossier(
        identity=identity,
        literature=[{"title": "Paper 1"}],
        cancer_lit=[{"title": "Cancer paper"}],
        sections=sections,
        critic_report=critic,
        provenance=_make_provenance(),
        convergence=0.75,
        cancer_type="colorectal",
    )

    assert dossier.gene_symbol == "TP53"
    assert dossier.cancer_type == "colorectal"
    assert dossier.convergence_score == 0.75
    assert len(dossier.sections) >= 2  # identity + overview + provenance
    assert len(dossier.claims) >= 2


def test_render_markdown():
    identity = _make_identity()
    claims = _make_claims()
    sections = [("Molecular Mechanisms", "TP53 acts as a transcription factor.", claims, ["abc"])]
    critic = CriticReport(claims_checked=2, revised_claims=claims)

    dossier = assemble_dossier(
        identity=identity,
        literature=[],
        cancer_lit=[],
        sections=sections,
        critic_report=critic,
        provenance=_make_provenance(),
        convergence=0.85,
        cancer_type="colorectal",
    )

    md = render_markdown(dossier)
    assert "# Gene Dossier: TP53" in md
    assert "colorectal" in md
    assert "0.850" in md
    assert "PMID:20301340" in md
    assert "Provenance" in md


def test_render_json():
    identity = _make_identity()
    sections = [("Test", "Content", [], ["abc"])]
    critic = CriticReport()

    dossier = assemble_dossier(
        identity=identity,
        literature=[],
        cancer_lit=[],
        sections=sections,
        critic_report=critic,
        provenance=[],
        convergence=0.5,
    )

    data = render_json(dossier)
    assert data["gene_symbol"] == "TP53"
    assert isinstance(data["sections"], list)
    assert "convergence_score" in data
