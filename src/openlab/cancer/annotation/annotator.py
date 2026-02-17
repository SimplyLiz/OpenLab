"""Multi-source variant annotator.

Orchestrates parallel annotation of variants against ClinVar, COSMIC,
OncoKB, and CIViC. Only sends gene symbol + HGVS to external APIs,
never raw VCF data.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from openlab.cancer.models.variant import (
    AnnotatedVariant,
    ClinicalSignificance,
    EvidenceItem,
    VariantRecord,
)

logger = logging.getLogger(__name__)


async def annotate_variants(
    variants: list[VariantRecord],
    http: httpx.AsyncClient,
    max_concurrency: int = 10,
) -> list[AnnotatedVariant]:
    """Annotate variants with evidence from cancer databases.

    Sends only gene_symbol and HGVS notation to APIs. Never sends raw VCF.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [_annotate_single(v, http, semaphore) for v in variants]
    return await asyncio.gather(*tasks)


async def _annotate_single(
    variant: VariantRecord,
    http: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> AnnotatedVariant:
    """Annotate a single variant from multiple sources."""
    async with semaphore:
        evidence: list[EvidenceItem] = []
        sources_queried: list[str] = []

        if variant.gene_symbol:
            # Run annotation sources in parallel
            results = await asyncio.gather(
                _query_clinvar(variant, http),
                _query_cosmic(variant, http),
                _query_oncokb(variant, http),
                _query_civic(variant, http),
                return_exceptions=True,
            )

            source_names = ["clinvar", "cosmic", "oncokb", "civic"]
            for name, result in zip(source_names, results, strict=True):
                if isinstance(result, BaseException):
                    logger.debug("Annotation source %s failed: %s", name, result)
                    continue
                if isinstance(result, list):
                    evidence.extend(result)
                    sources_queried.append(name)

        return AnnotatedVariant(
            variant=variant,
            evidence=evidence,
            annotation_sources=sources_queried,
        )


async def _query_clinvar(variant: VariantRecord, http: httpx.AsyncClient) -> list[EvidenceItem]:
    """Query ClinVar for variant evidence."""
    try:
        from openlab.contrib.cancer.sources.clinvar import search_clinvar
        result = await search_clinvar(http, variant.gene_symbol)
        items = []
        for v in result.get("variants", []):
            sig = _parse_clinical_significance(v.get("clinical_significance", ""))
            items.append(EvidenceItem(
                source="clinvar",
                classification=sig,
                evidence_level=v.get("review_status", ""),
                description=v.get("title", ""),
                source_url=v.get("_sources", [""])[0] if v.get("_sources") else "",
                confidence=_clinvar_confidence(v.get("review_status", "")),
            ))
        return items
    except Exception as e:
        logger.debug("ClinVar annotation failed: %s", e)
        return []


async def _query_cosmic(variant: VariantRecord, http: httpx.AsyncClient) -> list[EvidenceItem]:
    """Query COSMIC for variant evidence."""
    try:
        from openlab.contrib.cancer.sources.cosmic import search_cosmic
        result = await search_cosmic(http, variant.gene_symbol)
        items = []
        for m in result.get("mutations", []):
            items.append(EvidenceItem(
                source="cosmic",
                description=(
                    f"{m.get('gene_symbol', '')} "
                    f"{m.get('aa_mutation', '')} in "
                    f"{m.get('primary_site', '')}"
                ),
                source_url=m.get("_sources", [""])[0] if m.get("_sources") else "",
                confidence=0.6,
            ))
        return items
    except Exception as e:
        logger.debug("COSMIC annotation failed: %s", e)
        return []


async def _query_oncokb(variant: VariantRecord, http: httpx.AsyncClient) -> list[EvidenceItem]:
    """Query OncoKB for variant evidence."""
    try:
        from openlab.contrib.cancer.sources.oncokb import search_oncokb
        result = await search_oncokb(http, variant.gene_symbol)
        items = []
        for entry in result.get("entries", []):
            raw_t = entry.get("therapies")
            therapies = raw_t if isinstance(raw_t, list) else []
            items.append(EvidenceItem(
                source="oncokb",
                description=(
                    f"{entry.get('variant_name', '')} - "
                    f"{entry.get('oncogenic', '')}"
                ),
                therapies=therapies,
                source_url=entry.get("_sources", [""])[0] if entry.get("_sources") else "",
                confidence=0.8,
            ))
        return items
    except Exception as e:
        logger.debug("OncoKB annotation failed: %s", e)
        return []


async def _query_civic(variant: VariantRecord, http: httpx.AsyncClient) -> list[EvidenceItem]:
    """Query CIViC for variant evidence."""
    try:
        from openlab.contrib.cancer.sources.civic import search_civic
        result = await search_civic(http, variant.gene_symbol)
        items = []
        for entry in result.get("entries", []):
            if entry.get("record_type") != "evidence":
                continue
            raw_t = entry.get("therapies")
            therapies = raw_t if isinstance(raw_t, list) else []
            items.append(EvidenceItem(
                source="civic",
                evidence_level=entry.get("evidence_level", ""),
                description=entry.get("description", ""),
                pmids=[entry["pmid"]] if entry.get("pmid") else [],
                therapies=therapies,
                source_url=entry.get("_sources", [""])[0] if entry.get("_sources") else "",
                confidence=_civic_confidence(entry.get("evidence_level", "")),
            ))
        return items
    except Exception as e:
        logger.debug("CIViC annotation failed: %s", e)
        return []


def _parse_clinical_significance(sig: str) -> ClinicalSignificance | None:
    """Parse a clinical significance string into enum."""
    sig_lower = sig.lower()
    if "pathogenic" in sig_lower and "likely" not in sig_lower:
        return ClinicalSignificance.PATHOGENIC
    if "likely pathogenic" in sig_lower:
        return ClinicalSignificance.LIKELY_PATHOGENIC
    if "benign" in sig_lower and "likely" not in sig_lower:
        return ClinicalSignificance.BENIGN
    if "likely benign" in sig_lower:
        return ClinicalSignificance.LIKELY_BENIGN
    if "uncertain" in sig_lower or "vus" in sig_lower:
        return ClinicalSignificance.VUS
    return None


def _clinvar_confidence(review_status: str) -> float:
    """Map ClinVar review status to confidence score."""
    status_lower = review_status.lower()
    if "expert panel" in status_lower:
        return 0.95
    if "reviewed by" in status_lower:
        return 0.85
    if "multiple submitters" in status_lower:
        return 0.75
    if "single submitter" in status_lower:
        return 0.5
    return 0.3


def _civic_confidence(evidence_level: str) -> float:
    """Map CIViC evidence level to confidence."""
    level_map = {"A": 0.9, "B": 0.7, "C": 0.5, "D": 0.3, "E": 0.2}
    return level_map.get(evidence_level, 0.3)
