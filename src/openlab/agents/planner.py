"""Deterministic goal decomposition — fixed execution DAG for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlanStep:
    step_id: str
    tool_name: str
    arguments: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    phase: int = 0


@dataclass
class DossierPlan:
    steps: list[PlanStep] = field(default_factory=list)
    gene_symbol: str = ""
    cancer_type: str | None = None

    def phases(self) -> dict[int, list[PlanStep]]:
        result: dict[int, list[PlanStep]] = {}
        for step in self.steps:
            result.setdefault(step.phase, []).append(step)
        return result


def plan_gene_dossier(gene_symbol: str, cancer_type: str | None = None) -> DossierPlan:
    """Create a fixed execution plan for gene dossier generation.

    Phases:
      1. Identity (parallel) — ncbi_gene_info, ensembl_lookup, uniprot_lookup
      2. Evidence (parallel) — literature_search, cancer_literature, evidence_fetch
      3. Analysis (sequential) — convergence_score, llm_synthesize -> extract_claims
      4. Validation — critic.run_critic
      5. Assembly — reporter.assemble_dossier
    """
    steps = [
        # Phase 1: Identity
        PlanStep(
            step_id="ncbi",
            tool_name="ncbi_gene_info",
            arguments={"gene_symbol": gene_symbol},
            phase=1,
        ),
        PlanStep(
            step_id="ensembl",
            tool_name="ensembl_lookup",
            arguments={"gene_symbol": gene_symbol},
            phase=1,
        ),
        PlanStep(
            step_id="uniprot",
            tool_name="uniprot_lookup",
            arguments={"gene_symbol": gene_symbol},
            phase=1,
        ),
        # Phase 2: Evidence
        PlanStep(
            step_id="literature",
            tool_name="literature_search",
            arguments={"gene_symbol": gene_symbol},
            depends_on=["ncbi"],
            phase=2,
        ),
        PlanStep(
            step_id="cancer_lit",
            tool_name="cancer_literature",
            arguments={"gene_symbol": gene_symbol, "cancer_type": cancer_type or ""},
            depends_on=["ncbi"],
            phase=2,
        ),
        PlanStep(
            step_id="evidence",
            tool_name="evidence_fetch",
            arguments={},
            depends_on=["ncbi"],
            phase=2,
        ),
        # Phase 3: Analysis
        PlanStep(
            step_id="convergence",
            tool_name="convergence_score",
            arguments={},
            depends_on=["literature", "cancer_lit", "evidence"],
            phase=3,
        ),
        PlanStep(
            step_id="synthesis",
            tool_name="llm_synthesize",
            arguments={},
            depends_on=["convergence"],
            phase=3,
        ),
        # Phase 4: Validation
        PlanStep(
            step_id="critic",
            tool_name="critic",
            arguments={},
            depends_on=["synthesis"],
            phase=4,
        ),
        # Phase 5: Assembly
        PlanStep(
            step_id="assemble",
            tool_name="assemble_dossier",
            arguments={},
            depends_on=["critic"],
            phase=5,
        ),
    ]

    return DossierPlan(steps=steps, gene_symbol=gene_symbol, cancer_type=cancer_type)
