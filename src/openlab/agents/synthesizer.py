"""LLM hypothesis generation with structured claim extraction."""

from __future__ import annotations

import re
from typing import Any

from openlab.agents.agent_models import Claim
from openlab.agents.tools import ToolRegistry

CANCER_DOSSIER_SYSTEM_PROMPT = (
    "You are a cancer genomics expert producing a research dossier on a "
    "specific gene's role in cancer. "
    "Rules:\n"
    "1. EVERY factual claim MUST cite a source using "
    "[PMID:XXXXXXXX] or [DOI:10.XXXX/XXXXX] format.\n"
    "2. Claims without citations MUST be prefixed with [SPECULATIVE].\n"
    "3. For each claim, provide a confidence score (0.0-1.0) in parentheses.\n"
    "4. Structure your response with clear sections.\n"
    "5. Distinguish between well-established findings and emerging research.\n"
    "6. Note any conflicting evidence explicitly.\n"
)


async def synthesize_section(
    tools: ToolRegistry,
    section_name: str,
    gene_identity: dict[str, Any],
    evidence: list[dict],
    cancer_type: str | None = None,
    prior_sections: list[str] | None = None,
) -> tuple[str, list[Claim], list[str]]:
    """Synthesize a dossier section via LLM, returning markdown + extracted claims."""
    gene = gene_identity.get("gene_symbol", "unknown")
    prompt_parts = [
        f"## Section: {section_name}",
        f"Gene: {gene}",
    ]
    if cancer_type:
        prompt_parts.append(f"Cancer type: {cancer_type}")

    prompt_parts.append(f"\nEvidence ({len(evidence)} items):")
    for i, ev in enumerate(evidence[:20], 1):
        source = ev.get("source", ev.get("evidence_type", "unknown"))
        prompt_parts.append(f"  {i}. [{source}] {_summarize_evidence(ev)}")

    if prior_sections:
        prompt_parts.append(f"\nPrior sections already written: {', '.join(prior_sections)}")
        prompt_parts.append("Build on prior sections without repeating content.")

    prompt = "\n".join(prompt_parts)

    result = await tools.call("llm_synthesize", {"prompt": prompt})
    call_ids = [result.call_id] if result.success else []

    markdown = result.data.get("response", "") if result.success else ""
    claims = extract_claims(markdown)

    return markdown, claims, call_ids


def extract_claims(llm_response: str) -> list[Claim]:
    """Extract structured claims from LLM response text.

    Identifies citations ([PMID:X], [DOI:X]), speculation markers ([SPECULATIVE]),
    and confidence scores from parenthesized decimals.
    """
    claims: list[Claim] = []

    # Split into sentences (rough)
    sentences = re.split(r"(?<=[.!?])\s+", llm_response)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue

        # Extract citations
        pmids = re.findall(r"\[PMID:(\d+)\]", sentence)
        dois = re.findall(r"\[DOI:(10\.\S+?)\]", sentence)
        citations = [f"PMID:{p}" for p in pmids] + [f"DOI:{d}" for d in dois]

        # Check for speculation marker
        is_speculative = "[SPECULATIVE]" in sentence

        # Extract confidence
        conf_match = re.search(r"\((\d\.\d+)\)", sentence)
        confidence = float(conf_match.group(1)) if conf_match else 0.0

        # Claims without citations get confidence=0.0 and marked speculative
        if not citations:
            confidence = 0.0
            is_speculative = True

        # Clean the claim text
        claim_text = sentence
        claim_text = re.sub(r"\[PMID:\d+\]", "", claim_text)
        claim_text = re.sub(r"\[DOI:10\.\S+?\]", "", claim_text)
        claim_text = re.sub(r"\[SPECULATIVE\]", "", claim_text)
        claim_text = re.sub(r"\(\d\.\d+\)", "", claim_text)
        claim_text = claim_text.strip()

        if len(claim_text) > 15:
            claims.append(
                Claim(
                    claim_text=claim_text,
                    confidence=confidence,
                    citations=citations,
                    is_speculative=is_speculative,
                )
            )

    return claims


def _summarize_evidence(ev: dict) -> str:
    """Create a brief summary of an evidence item for the LLM prompt."""
    parts = []
    for key in ("title", "description", "product", "name", "clinical_significance"):
        val = ev.get(key)
        if val:
            parts.append(str(val)[:100])
    if not parts:
        payload = ev.get("payload", {})
        if isinstance(payload, dict):
            for key in ("description", "predicted_function", "summary"):
                val = payload.get(key)
                if val:
                    parts.append(str(val)[:100])
                    break
    return "; ".join(parts) if parts else str(ev)[:80]
