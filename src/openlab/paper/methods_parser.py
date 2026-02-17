"""Parse methods text into structured protocol steps.

Uses regex-based extraction for common protocol patterns. For ambiguous
text, steps are marked with lower confidence.
"""

from __future__ import annotations

import logging
import re

from openlab.paper.protocol_models import ExtractedProtocol, ProtocolStep, Reagent

logger = logging.getLogger(__name__)

# Technique detection patterns
_TECHNIQUE_PATTERNS = [
    (r"(?i)\b(RNA[- ]?seq(?:uencing)?)\b", "RNA-seq"),
    (r"(?i)\b(ChIP[- ]?seq(?:uencing)?)\b", "ChIP-seq"),
    (r"(?i)\b(ATAC[- ]?seq(?:uencing)?)\b", "ATAC-seq"),
    (r"(?i)\b(whole[- ]?genome[- ]?sequencing|WGS)\b", "whole genome sequencing"),
    (r"(?i)\b(whole[- ]?exome[- ]?sequencing|WES)\b", "whole exome sequencing"),
    (r"(?i)\b(single[- ]?cell[- ]?RNA[- ]?seq|scRNA[- ]?seq)\b", "single cell RNA-seq"),
    (r"(?i)\b(mass[- ]?spectrometry|LC[- ]?MS/?MS|proteomics)\b", "mass spectrometry"),
    (r"(?i)\b(flow[- ]?cytometry|FACS)\b", "flow cytometry"),
    (r"(?i)\b(differential[- ]?expression)\b", "differential expression"),
    (r"(?i)\b(gene[- ]?set[- ]?enrichment|GSEA)\b", "gene set enrichment"),
    (r"(?i)\b(variant[- ]?calling)\b", "variant calling"),
    (r"(?i)\b(PCR|polymerase chain reaction)\b", "PCR"),
    (r"(?i)\b(western[- ]?blot(?:ting)?)\b", "western blot"),
    (r"(?i)\b(cell[- ]?culture)\b", "cell culture"),
    (r"(?i)\b(transfection)\b", "transfection"),
    (r"(?i)\b(CRISPR|Cas9)\b", "CRISPR"),
    (r"(?i)\b(immunohistochemistry|IHC)\b", "immunohistochemistry"),
    (r"(?i)\b(qPCR|RT-qPCR|quantitative PCR)\b", "qPCR"),
]

# Reagent patterns
_REAGENT_PATTERN = re.compile(
    r"(\d+[\.\d]*\s*(?:µ[LMlm]|m[LMlm]|[nuμ][gGMm]|%|mM|µM|nM)\s+[\w\s-]+)"
)

# Temperature pattern
_TEMP_PATTERN = re.compile(r"(\d+)\s*°?\s*C")

# Duration pattern
_DURATION_PATTERN = re.compile(
    r"(\d+[\.\d]*)\s*(min(?:ute)?s?|h(?:our)?s?|sec(?:ond)?s?|days?)"
)


def parse_methods(
    methods_text: str,
    paper_title: str = "",
    paper_doi: str = "",
) -> ExtractedProtocol:
    """Parse methods text into a structured protocol."""
    # Detect techniques
    techniques = _detect_techniques(methods_text)

    # Split into paragraphs and parse each as potential steps
    paragraphs = [p.strip() for p in methods_text.split("\n\n") if p.strip()]
    steps = []
    step_num = 0

    for para in paragraphs:
        para_techniques = _detect_techniques(para)
        if para_techniques or _looks_like_protocol_step(para):
            step_num += 1
            technique = para_techniques[0] if para_techniques else ""
            steps.append(ProtocolStep(
                step_number=step_num,
                technique=technique,
                description=_clean_description(para),
                parameters=_extract_parameters(para),
                reagents=_extract_reagent_names(para),
                temperature=_extract_temperature(para),
                duration=_extract_duration(para),
                confidence=0.8 if technique else 0.4,
            ))

    # Extract reagents
    reagents = _extract_reagents(methods_text)

    # Detect organisms
    organisms = _detect_organisms(methods_text)

    return ExtractedProtocol(
        title=paper_title,
        paper_doi=paper_doi,
        steps=steps,
        reagents=reagents,
        organisms=organisms,
        techniques_mentioned=techniques,
        raw_methods_text=methods_text,
    )


def _detect_techniques(text: str) -> list[str]:
    """Detect bioinformatics/lab techniques mentioned in text."""
    found = []
    for pattern, name in _TECHNIQUE_PATTERNS:
        if re.search(pattern, text) and name not in found:
            found.append(name)
    return found


def _looks_like_protocol_step(text: str) -> bool:
    """Heuristic: does this paragraph look like a protocol step?"""
    keywords = [
        "incubat", "centrifug", "resuspend", "wash", "elut",
        "performed", "protocol", "according to", "manufacturer",
        "sequenc", "analyz", "align", "extract", "purif",
        "harvest", "digest", "ligate", "amplif", "quantif",
    ]
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower) >= 2


def _clean_description(text: str) -> str:
    """Clean up paragraph text for use as a step description."""
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Truncate if too long
    if len(text) > 500:
        text = text[:497] + "..."
    return text


def _extract_parameters(text: str) -> dict:
    """Extract common parameters from text."""
    params = {}
    temp = _extract_temperature(text)
    if temp:
        params["temperature"] = temp
    dur = _extract_duration(text)
    if dur:
        params["duration"] = dur
    return params


def _extract_temperature(text: str) -> str:
    """Extract temperature from text."""
    match = _TEMP_PATTERN.search(text)
    return f"{match.group(1)}°C" if match else ""


def _extract_duration(text: str) -> str:
    """Extract duration from text."""
    match = _DURATION_PATTERN.search(text)
    return f"{match.group(1)} {match.group(2)}" if match else ""


def _extract_reagent_names(text: str) -> list[str]:
    """Extract reagent names from text (simplified)."""
    matches = _REAGENT_PATTERN.findall(text)
    return [m.strip() for m in matches[:10]]


def _extract_reagents(text: str) -> list[Reagent]:
    """Extract structured reagent information."""
    reagents = []
    matches = _REAGENT_PATTERN.findall(text)
    for match in matches[:20]:
        parts = match.strip().split()
        if len(parts) >= 2:
            # First part is likely concentration/volume
            conc = parts[0] + " " + parts[1] if len(parts) > 1 else parts[0]
            name = " ".join(parts[2:]) if len(parts) > 2 else ""
            if name:
                reagents.append(Reagent(name=name, concentration=conc))
    return reagents


def _detect_organisms(text: str) -> list[str]:
    """Detect organism names mentioned in text."""
    organisms = []
    patterns = [
        (r"(?i)\b(Homo sapiens|human)\b", "Homo sapiens"),
        (r"(?i)\b(Mus musculus|mouse|mice)\b", "Mus musculus"),
        (r"(?i)\b(Escherichia coli|E\. coli)\b", "Escherichia coli"),
        (r"(?i)\b(Saccharomyces cerevisiae|yeast)\b", "Saccharomyces cerevisiae"),
        (r"(?i)\b(Drosophila melanogaster|fruit fly)\b", "Drosophila melanogaster"),
        (r"(?i)\b(Caenorhabditis elegans|C\. elegans)\b", "Caenorhabditis elegans"),
        (r"(?i)\b(Danio rerio|zebrafish)\b", "Danio rerio"),
        (r"(?i)\b(Arabidopsis thaliana)\b", "Arabidopsis thaliana"),
    ]
    for pattern, name in patterns:
        if re.search(pattern, text) and name not in organisms:
            organisms.append(name)
    return organisms
