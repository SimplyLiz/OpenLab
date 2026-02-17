"""QA validation — citation checking, overclaiming detection, circular reasoning."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from openlab.agents.agent_models import CitationStatus, Claim
from openlab.agents.tools import ToolRegistry


@dataclass
class CriticReport:
    claims_checked: int = 0
    citations_valid: int = 0
    citations_invalid: int = 0
    overclaiming_flags: list[str] = field(default_factory=list)
    circular_reasoning_flags: list[str] = field(default_factory=list)
    revised_claims: list[Claim] = field(default_factory=list)


async def run_critic(
    tools: ToolRegistry,
    claims: list[Claim],
    evidence_sources: list[str],
) -> tuple[CriticReport, list[str]]:
    """Run full critic pipeline: validate citations, overclaiming, circular reasoning."""
    report = CriticReport(claims_checked=len(claims))
    call_ids: list[str] = []

    # Validate citations
    validated, validation_call_ids = await validate_citations(tools, claims)
    call_ids.extend(validation_call_ids)

    for claim in validated:
        if claim.citation_status == CitationStatus.VALID:
            report.citations_valid += len(claim.citations)
        elif claim.citation_status == CitationStatus.INVALID:
            report.citations_invalid += len(claim.citations)

    # Detect overclaiming
    report.overclaiming_flags = detect_overclaiming(validated, len(evidence_sources))

    # Detect circular reasoning
    report.circular_reasoning_flags = detect_circular_reasoning(validated, call_ids)

    report.revised_claims = validated
    return report, call_ids


async def validate_citations(
    tools: ToolRegistry, claims: list[Claim]
) -> tuple[list[Claim], list[str]]:
    """Batch-validate PMIDs/DOIs via EuropePMC. Max 10 concurrent."""
    sem = asyncio.Semaphore(10)
    call_ids: list[str] = []

    # Collect unique PMIDs to validate
    pmids_to_check: set[str] = set()
    for claim in claims:
        for cit in claim.citations:
            if cit.startswith("PMID:"):
                pmids_to_check.add(cit.replace("PMID:", ""))

    # Validate each PMID
    valid_pmids: set[str] = set()
    invalid_pmids: set[str] = set()

    async def _check_pmid(pmid: str) -> None:
        async with sem:
            result = await tools.call("pmid_validate", {"pmid": pmid})
            if result.success:
                call_ids.append(result.call_id)
                if result.data.get("valid"):
                    valid_pmids.add(pmid)
                else:
                    invalid_pmids.add(pmid)

    await asyncio.gather(*[_check_pmid(p) for p in pmids_to_check])

    # Update claims with validation status
    validated: list[Claim] = []
    for claim in claims:
        new_claim = claim.model_copy()
        if not claim.citations:
            new_claim.citation_status = CitationStatus.UNCHECKED
            new_claim.is_speculative = True
            new_claim.confidence = 0.0
        else:
            has_valid = any(
                cit.replace("PMID:", "") in valid_pmids
                for cit in claim.citations
                if cit.startswith("PMID:")
            )
            has_invalid = any(
                cit.replace("PMID:", "") in invalid_pmids
                for cit in claim.citations
                if cit.startswith("PMID:")
            )
            if has_invalid and not has_valid:
                new_claim.citation_status = CitationStatus.INVALID
            elif has_valid:
                new_claim.citation_status = CitationStatus.VALID
            else:
                # DOI-only citations stay UNCHECKED for now
                new_claim.citation_status = CitationStatus.UNCHECKED
        validated.append(new_claim)

    return validated, call_ids


def detect_overclaiming(claims: list[Claim], evidence_count: int) -> list[str]:
    """Flag claims with high confidence but insufficient citations."""
    flags: list[str] = []
    for claim in claims:
        if claim.confidence > 0.7 and len(claim.citations) < 2:
            flags.append(
                f"Overclaiming: '{claim.claim_text[:60]}...' has confidence "
                f"{claim.confidence} but only {len(claim.citations)} citation(s)"
            )
    if evidence_count < 3 and any(c.confidence > 0.8 for c in claims):
        flags.append(
            f"Overclaiming: high confidence claims with only {evidence_count} evidence sources"
        )
    return flags


def detect_circular_reasoning(claims: list[Claim], tool_call_ids: list[str]) -> list[str]:
    """Detect potential circular reasoning patterns."""
    flags: list[str] = []
    # Check for claims that cite only LLM-generated sources
    for claim in claims:
        if claim.citations and all(
            "llm" in cit.lower() or "synthesis" in cit.lower() for cit in claim.citations
        ):
            flags.append(
                f"Circular reasoning: '{claim.claim_text[:60]}...' cites only LLM-derived sources"
            )
    return flags
