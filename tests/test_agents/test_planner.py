"""Tests for deterministic plan generation."""

from openlab.agents.planner import plan_gene_dossier


def test_plan_gene_dossier_basic():
    plan = plan_gene_dossier("TP53", "colorectal")
    assert plan.gene_symbol == "TP53"
    assert plan.cancer_type == "colorectal"
    assert len(plan.steps) > 0


def test_plan_has_five_phases():
    plan = plan_gene_dossier("BRAF", "melanoma")
    phases = plan.phases()
    assert set(phases.keys()) == {1, 2, 3, 4, 5}


def test_phase_1_identity():
    plan = plan_gene_dossier("TP53")
    phases = plan.phases()
    phase1_tools = [s.tool_name for s in phases[1]]
    assert "ncbi_gene_info" in phase1_tools
    assert "ensembl_lookup" in phase1_tools
    assert "uniprot_lookup" in phase1_tools


def test_phase_2_evidence():
    plan = plan_gene_dossier("TP53", "colorectal")
    phases = plan.phases()
    phase2_tools = [s.tool_name for s in phases[2]]
    assert "literature_search" in phase2_tools
    assert "cancer_literature" in phase2_tools


def test_dependencies():
    plan = plan_gene_dossier("TP53")
    # Phase 1 steps should have no dependencies
    phases = plan.phases()
    for step in phases[1]:
        assert step.depends_on == []
    # Phase 2 steps should depend on phase 1
    for step in phases[2]:
        assert len(step.depends_on) > 0


def test_plan_without_cancer():
    plan = plan_gene_dossier("GAPDH")
    assert plan.cancer_type is None
    # Should still have cancer_literature step (with empty cancer_type)
    step_names = [s.tool_name for s in plan.steps]
    assert "cancer_literature" in step_names
