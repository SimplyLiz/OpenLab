"""DNASyn contrib module — evidence sources for JCVI-syn3A functional annotation.

Registers 18 evidence producers with BioLab's source registry.
Import this module to activate DNASyn sources:

    import openlab.contrib.dnasyn  # registers all sources

Or selectively:
    from openlab.contrib.dnasyn import register_all
    register_all()
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register_all() -> None:
    """Register all DNASyn evidence sources with the BioLab registry."""
    global _registered
    if _registered:
        return

    from openlab.db.models.evidence import EvidenceType
    from openlab.registry import register_source

    _MOD = "openlab.contrib.dnasyn.sources"

    # ── API-based sources ──────────────────────────────────────────

    register_source(
        name="esmfold",
        evidence_type=EvidenceType.STRUCTURE,
        module_path=f"{_MOD}.esmfold",
        runner_func="run_esmfold",
        async_func="search_esmfold",
        description="ESMFold structure prediction via HuggingFace",
        group="dnasyn",
        convergence_weight=0.1,
    )
    register_source(
        name="alphafold",
        evidence_type=EvidenceType.STRUCTURE,
        module_path=f"{_MOD}.alphafold",
        runner_func="run_alphafold",
        async_func="search_alphafold",
        description="AlphaFold DB structure retrieval",
        group="dnasyn",
        convergence_weight=0.3,
    )
    register_source(
        name="foldseek",
        evidence_type=EvidenceType.STRUCTURE,
        module_path=f"{_MOD}.foldseek",
        runner_func="run_foldseek",
        async_func="search_foldseek",
        description="Foldseek online structural similarity search",
        group="dnasyn",
        convergence_weight=1.5,
    )
    register_source(
        name="hhpred",
        evidence_type=EvidenceType.HOMOLOGY,
        module_path=f"{_MOD}.hhpred",
        runner_func="run_hhpred",
        async_func="search_hhpred",
        description="HHpred remote homology via MPI Toolkit",
        group="dnasyn",
        convergence_weight=1.8,
    )
    register_source(
        name="synwiki",
        evidence_type=EvidenceType.LITERATURE,
        module_path=f"{_MOD}.synwiki",
        runner_func="run_synwiki",
        async_func="search_synwiki",
        description="SynWiki curated annotations",
        group="dnasyn",
        convergence_weight=1.5,
    )
    register_source(
        name="eggnog_online",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.eggnog_online",
        runner_func="run_eggnog_online",
        async_func="search_eggnog_online",
        description="eggNOG-mapper online API",
        group="dnasyn",
        convergence_weight=1.8,
    )
    register_source(
        name="europepmc",
        evidence_type=EvidenceType.LITERATURE,
        module_path=f"{_MOD}.europepmc",
        runner_func="run_europepmc",
        async_func="search_europepmc",
        description="Enhanced EuropePMC literature search",
        group="dnasyn",
        convergence_weight=0.2,
    )

    # ── Local tool sources ─────────────────────────────────────────

    register_source(
        name="hmmscan",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.hmmscan",
        runner_func="run_hmmscan",
        description="hmmscan against Pfam database",
        group="dnasyn",
        convergence_weight=1.5,
    )
    register_source(
        name="hhblits",
        evidence_type=EvidenceType.HOMOLOGY,
        module_path=f"{_MOD}.hhblits",
        runner_func="run_hhblits",
        description="HHblits local profile-profile search",
        group="dnasyn",
        convergence_weight=1.8,
    )
    register_source(
        name="prost",
        evidence_type=EvidenceType.HOMOLOGY,
        module_path=f"{_MOD}.prost",
        runner_func="run_prost",
        description="PROST structure-based homology transfer",
        group="dnasyn",
        convergence_weight=1.5,
    )
    register_source(
        name="deeptmhmm",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.deeptmhmm",
        runner_func="run_deeptmhmm",
        description="DeepTMHMM transmembrane topology prediction",
        group="dnasyn",
        convergence_weight=0.1,
    )
    register_source(
        name="signalp",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.signalp",
        runner_func="run_signalp",
        description="SignalP 6.0 signal peptide prediction",
        group="dnasyn",
        convergence_weight=0.1,
    )
    register_source(
        name="phylogenetic_profile",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.phylo_profiles",
        runner_func="run_phylogenetic_profile",
        description="Phylogenetic profiling via DIAMOND BLAST",
        group="dnasyn",
        convergence_weight=0.5,
    )
    register_source(
        name="operon_prediction",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.operon",
        runner_func="run_operon_prediction",
        description="Operon prediction from genomic organization",
        group="dnasyn",
        convergence_weight=0.3,
    )
    register_source(
        name="genomic_neighborhood",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.neighborhood",
        runner_func="run_genomic_neighborhood",
        description="Genomic neighborhood context",
        group="dnasyn",
        convergence_weight=0.3,
    )
    register_source(
        name="foldseek_local",
        evidence_type=EvidenceType.STRUCTURE,
        module_path=f"{_MOD}.foldseek_local",
        runner_func="run_foldseek_local",
        description="Foldseek local structural similarity",
        group="dnasyn",
        convergence_weight=1.5,
    )
    register_source(
        name="eggnog_local",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.eggnog_local",
        runner_func="run_eggnog_local",
        description="eggNOG-mapper local annotation",
        group="dnasyn",
        convergence_weight=1.8,
    )

    # Source alias: eggnog_local and eggnog_online both persist as "eggnog"
    # The dedup in evidence_runner uses source_ref, so they won't collide.

    _registered = True
    logger.info("DNASyn: registered %d evidence sources", 17)


# Auto-register on import
try:
    register_all()
except Exception as e:
    logger.debug("DNASyn auto-register deferred: %s", e)
