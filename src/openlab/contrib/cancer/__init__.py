"""Cancer contrib module — evidence sources for cancer gene research.

Registers 6 cancer-specific evidence sources with OpenLab's source registry.
Import this module to activate cancer sources:

    import openlab.contrib.cancer  # registers all sources
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register_all() -> None:
    """Register all cancer evidence sources with the OpenLab registry."""
    global _registered
    if _registered:
        return

    from openlab.db.models.evidence import EvidenceType
    from openlab.registry import register_source

    _MOD = "openlab.contrib.cancer.sources"

    register_source(
        name="clinvar",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.clinvar",
        runner_func="run_clinvar",
        async_func="search_clinvar",
        description="ClinVar variant-disease associations (NCBI)",
        group="cancer",
        convergence_weight=1.8,
    )
    register_source(
        name="cosmic",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.cosmic",
        runner_func="run_cosmic",
        async_func="search_cosmic",
        description="COSMIC somatic mutation catalogue",
        group="cancer",
        convergence_weight=2.0,
    )
    register_source(
        name="oncokb",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.oncokb",
        runner_func="run_oncokb",
        async_func="search_oncokb",
        description="OncoKB precision oncology knowledge base",
        group="cancer",
        convergence_weight=2.0,
    )
    register_source(
        name="cbioportal",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.cbioportal",
        runner_func="run_cbioportal",
        async_func="search_cbioportal",
        description="cBioPortal cancer genomics (open API)",
        group="cancer",
        convergence_weight=1.5,
    )
    register_source(
        name="civic",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.civic",
        runner_func="run_civic",
        async_func="search_civic",
        description="CIViC clinical interpretations (CC0)",
        group="cancer",
        convergence_weight=1.8,
    )
    register_source(
        name="tcga_gdc",
        evidence_type=EvidenceType.COMPUTATIONAL,
        module_path=f"{_MOD}.tcga_gdc",
        runner_func="run_tcga_gdc",
        async_func="search_tcga_gdc",
        description="TCGA/GDC mutation frequencies",
        group="cancer",
        convergence_weight=1.5,
    )

    _registered = True
    logger.info("Cancer: registered 6 evidence sources")


# Auto-register on import
try:
    register_all()
except Exception as e:
    logger.debug("Cancer auto-register deferred: %s", e)
