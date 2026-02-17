"""Variant interpretation data models."""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class GenomeBuild(enum.StrEnum):
    HG19 = "hg19"
    HG38 = "hg38"
    GRCH37 = "GRCh37"
    GRCH38 = "GRCh38"

    def is_hg38(self) -> bool:
        return self in (GenomeBuild.HG38, GenomeBuild.GRCH38)

    def is_hg19(self) -> bool:
        return self in (GenomeBuild.HG19, GenomeBuild.GRCH37)


class ClinicalSignificance(enum.StrEnum):
    PATHOGENIC = "pathogenic"
    LIKELY_PATHOGENIC = "likely_pathogenic"
    VUS = "uncertain_significance"
    LIKELY_BENIGN = "likely_benign"
    BENIGN = "benign"


class VariantRecord(BaseModel):
    """Raw variant parsed from VCF."""
    chrom: str
    pos: int
    ref: str
    alt: str
    quality: float | None = None
    filter_status: str = "."
    gene_symbol: str = ""
    hgvs_g: str = ""
    hgvs_c: str = ""
    hgvs_p: str = ""
    info: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    """Single evidence item from an annotation source."""
    source: str
    classification: ClinicalSignificance | None = None
    evidence_level: str = ""
    description: str = ""
    source_url: str = ""
    pmids: list[str] = Field(default_factory=list)
    therapies: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class AnnotatedVariant(BaseModel):
    """Variant with multi-source annotations."""
    variant: VariantRecord
    evidence: list[EvidenceItem] = Field(default_factory=list)
    consensus_classification: ClinicalSignificance = ClinicalSignificance.VUS
    confidence: float = 0.0
    is_actionable: bool = False
    annotation_sources: list[str] = Field(default_factory=list)


_DISCLAIMER = (
    "FOR RESEARCH USE ONLY. This is not a validated clinical"
    " diagnostic tool. Do not use for clinical decision-making."
)


class VariantReport(BaseModel):
    """Complete variant interpretation report."""
    disclaimer: str = Field(default=_DISCLAIMER, frozen=True)
    sample_id: str = ""
    tumor_type: str = ""
    genome_build: GenomeBuild = GenomeBuild.HG38
    variants: list[AnnotatedVariant] = Field(default_factory=list)
    total_variants_parsed: int = 0
    total_annotated: int = 0
    total_pathogenic: int = 0
    total_actionable: int = 0
    summary: str = ""
    reproducibility: dict[str, Any] = Field(default_factory=dict)
