"""Map extracted protocol steps to pipeline stages.

Uses deterministic mapping for known bioinformatics techniques,
with TODO annotations for steps that cannot be automatically resolved.
"""

from __future__ import annotations

import logging
import re

from openlab.paper.protocol_models import (
    ExtractedProtocol,
    PipelineConfig,
    PipelineStage,
    ProtocolStep,
)

logger = logging.getLogger(__name__)

# Known technique -> pipeline stage mapping
_TECHNIQUE_MAP: dict[str, dict] = {
    "rna-seq": {
        "tool": "STAR + featureCounts",
        "description": "RNA-seq alignment and quantification",
        "inputs": ["fastq_r1", "fastq_r2", "genome_index"],
        "outputs": ["counts_matrix"],
    },
    "rnaseq": {
        "tool": "STAR + featureCounts",
        "description": "RNA-seq alignment and quantification",
        "inputs": ["fastq_r1", "fastq_r2", "genome_index"],
        "outputs": ["counts_matrix"],
    },
    "chip-seq": {
        "tool": "BWA-MEM + MACS2",
        "description": "ChIP-seq alignment and peak calling",
        "inputs": ["fastq_treatment", "fastq_input", "genome_index"],
        "outputs": ["peaks_bed", "bigwig"],
    },
    "chipseq": {
        "tool": "BWA-MEM + MACS2",
        "description": "ChIP-seq alignment and peak calling",
        "inputs": ["fastq_treatment", "fastq_input", "genome_index"],
        "outputs": ["peaks_bed", "bigwig"],
    },
    "atac-seq": {
        "tool": "BWA-MEM + MACS2",
        "description": "ATAC-seq alignment and peak calling",
        "inputs": ["fastq_r1", "fastq_r2", "genome_index"],
        "outputs": ["peaks_bed", "bigwig"],
    },
    "whole genome sequencing": {
        "tool": "BWA-MEM + GATK",
        "description": "WGS alignment and variant calling",
        "inputs": ["fastq_r1", "fastq_r2", "genome_ref"],
        "outputs": ["aligned_bam", "vcf"],
    },
    "wgs": {
        "tool": "BWA-MEM + GATK",
        "description": "WGS alignment and variant calling",
        "inputs": ["fastq_r1", "fastq_r2", "genome_ref"],
        "outputs": ["aligned_bam", "vcf"],
    },
    "whole exome sequencing": {
        "tool": "BWA-MEM + GATK",
        "description": "WES alignment and variant calling",
        "inputs": ["fastq_r1", "fastq_r2", "genome_ref", "exome_targets"],
        "outputs": ["aligned_bam", "vcf"],
    },
    "wes": {
        "tool": "BWA-MEM + GATK",
        "description": "WES alignment and variant calling",
        "inputs": ["fastq_r1", "fastq_r2", "genome_ref", "exome_targets"],
        "outputs": ["aligned_bam", "vcf"],
    },
    "differential expression": {
        "tool": "DESeq2",
        "description": "Differential expression analysis",
        "inputs": ["counts_matrix", "sample_metadata"],
        "outputs": ["de_results"],
    },
    "gene set enrichment": {
        "tool": "fgsea",
        "description": "Gene set enrichment analysis",
        "inputs": ["de_results", "gene_sets"],
        "outputs": ["gsea_results"],
    },
    "gsea": {
        "tool": "fgsea",
        "description": "Gene set enrichment analysis",
        "inputs": ["de_results", "gene_sets"],
        "outputs": ["gsea_results"],
    },
    "variant calling": {
        "tool": "GATK HaplotypeCaller",
        "description": "Variant calling from aligned BAM",
        "inputs": ["aligned_bam", "genome_ref"],
        "outputs": ["vcf"],
    },
    "pcr": {
        "tool": "wet_lab",
        "description": "PCR amplification",
        "inputs": ["template_dna", "primers"],
        "outputs": ["amplified_product"],
        "manual_review": True,
    },
    "western blot": {
        "tool": "wet_lab",
        "description": "Western blot protein detection",
        "inputs": ["protein_lysate", "antibody"],
        "outputs": ["blot_image"],
        "manual_review": True,
    },
    "cell culture": {
        "tool": "wet_lab",
        "description": "Cell culture and maintenance",
        "inputs": ["cell_line", "media"],
        "outputs": ["cultured_cells"],
        "manual_review": True,
    },
    "flow cytometry": {
        "tool": "FlowJo",
        "description": "Flow cytometry analysis",
        "inputs": ["fcs_files"],
        "outputs": ["gating_results"],
    },
    "single cell rna-seq": {
        "tool": "CellRanger + Seurat",
        "description": "Single-cell RNA-seq processing",
        "inputs": ["fastq_r1", "fastq_r2", "genome_ref"],
        "outputs": ["count_matrix", "clusters"],
    },
    "scrna-seq": {
        "tool": "CellRanger + Seurat",
        "description": "Single-cell RNA-seq processing",
        "inputs": ["fastq_r1", "fastq_r2", "genome_ref"],
        "outputs": ["count_matrix", "clusters"],
    },
    "mass spectrometry": {
        "tool": "MaxQuant",
        "description": "Mass spectrometry proteomics analysis",
        "inputs": ["raw_files"],
        "outputs": ["protein_groups"],
    },
    "proteomics": {
        "tool": "MaxQuant",
        "description": "Proteomics data analysis",
        "inputs": ["raw_files"],
        "outputs": ["protein_groups"],
    },
}


def map_protocol_to_pipeline(protocol: ExtractedProtocol) -> PipelineConfig:
    """Map an extracted protocol to a pipeline configuration."""
    stages: list[PipelineStage] = []
    warnings: list[str] = []
    prev_stage_name: str | None = None

    for step in protocol.steps:
        stage = _map_step(step)
        if stage:
            if prev_stage_name and stage.name != prev_stage_name:
                stage.depends_on = [prev_stage_name]
            stages.append(stage)
            prev_stage_name = stage.name
        else:
            # Unresolvable step
            stage = PipelineStage(
                name=f"step_{step.step_number}_manual",
                tool="",
                description=step.description or step.technique,
                manual_review=True,
                notes=(
                    "# TODO: manual review required"
                    f" — could not auto-map technique: {step.technique}"
                ),
            )
            if prev_stage_name:
                stage.depends_on = [prev_stage_name]
            stages.append(stage)
            prev_stage_name = stage.name
            warnings.append(
                f"Step {step.step_number}: could not map"
                f" '{step.technique}' to a pipeline stage"
            )

    return PipelineConfig(
        name=protocol.title or "Extracted Pipeline",
        description="Pipeline extracted from paper methods section",
        source_paper=protocol.title,
        source_doi=protocol.paper_doi,
        stages=stages,
        warnings=warnings,
    )


def _map_step(step: ProtocolStep) -> PipelineStage | None:
    """Map a single protocol step to a pipeline stage."""
    technique = step.technique.lower().strip()

    # Direct mapping
    if technique in _TECHNIQUE_MAP:
        mapping = _TECHNIQUE_MAP[technique]
        return PipelineStage(
            name=_slugify(step.technique),
            tool=mapping["tool"],
            description=mapping.get("description", step.description),
            inputs=mapping.get("inputs", []),
            outputs=mapping.get("outputs", []),
            parameters=step.parameters,
            manual_review=mapping.get("manual_review", False),
        )

    # Fuzzy matching — check if technique contains a known key
    for key, mapping in _TECHNIQUE_MAP.items():
        if key in technique or technique in key:
            return PipelineStage(
                name=_slugify(step.technique),
                tool=mapping["tool"],
                description=mapping.get("description", step.description),
                inputs=mapping.get("inputs", []),
                outputs=mapping.get("outputs", []),
                parameters=step.parameters,
                manual_review=mapping.get("manual_review", False),
            )

    return None


def _slugify(text: str) -> str:
    """Convert text to a slug suitable for stage names."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug or "unnamed"
