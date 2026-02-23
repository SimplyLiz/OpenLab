"""LLM hypothesis generation with structured claim extraction."""

from __future__ import annotations

import re
from typing import Any

from openlab.agents.agent_models import Claim
from openlab.agents.tools import ToolRegistry

CANCER_DOSSIER_SYSTEM_PROMPT = (
    "You are a cancer genomics expert producing a research dossier.\n\n"
    "CITATION FORMAT (mandatory):\n"
    "- Place citations inline: 'TP53 is mutated in 50% of cancers [PMID:12345678] (0.9).'\n"
    "- Use [PMID:NUMBER] or [DOI:10.xxxx/xxxx] format ONLY.\n"
    "- Do NOT use [PubMed:NUMBER] — use [PMID:NUMBER] instead.\n"
    "- Do NOT use numbered footnotes like [1], [2] with a reference list.\n"
    "- Do NOT add a 'References' section at the end.\n\n"
    "CONFIDENCE SCORES:\n"
    "- Add (0.0-1.0) after each claim: "
    "'...poor prognosis [PMID:98765432] (0.85).'\n\n"
    "SPECULATIVE CLAIMS:\n"
    "- Prefix uncited claims: '[SPECULATIVE] This pathway may be involved (0.3).'\n\n"
    "STRUCTURE:\n"
    "- Do NOT write the section title — it is already handled by the system.\n"
    "- Use ### subheadings within sections as needed.\n"
    "- Distinguish established findings from emerging research.\n"
    "- Note conflicting evidence explicitly.\n"
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
        f"Write the content for the dossier section titled '{section_name}'.",
        "Do NOT include the section title as a heading — it is already handled.",
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

    result = await tools.call("llm_synthesize", {
        "prompt": prompt,
        "system_prompt": CANCER_DOSSIER_SYSTEM_PROMPT,
    })
    call_ids = [result.call_id] if result.success else []

    markdown = result.data.get("response", "") if result.success else ""
    claims = extract_claims(markdown)

    return markdown, claims, call_ids


def _build_footnote_map(text: str) -> dict[int, list[str]]:
    """Scan for footnote-style reference lists and map numbers to PMIDs/DOIs."""
    mapping: dict[int, list[str]] = {}
    for m in re.finditer(
        r"^\[(\d+)\]\s*(?:\[?(?:PMID|PubMed):\s*(\d+)\]?|\[?DOI:\s*(10\.\S+?)\]?)",
        text, re.MULTILINE,
    ):
        num = int(m.group(1))
        cites: list[str] = []
        if m.group(2):
            cites.append(f"PMID:{m.group(2)}")
        if m.group(3):
            cites.append(f"DOI:{m.group(3)}")
        if cites:
            mapping[num] = cites
    return mapping


def extract_claims(llm_response: str) -> list[Claim]:
    """Extract structured claims from LLM response text.

    Identifies citations ([PMID:X], [DOI:X]), speculation markers ([SPECULATIVE]),
    and confidence scores from parenthesized decimals. Also resolves footnote-style
    references like [1] when a reference list is present at the end.
    """
    claims: list[Claim] = []
    footnote_map = _build_footnote_map(llm_response)

    # Split into sentences (rough)
    sentences = re.split(r"(?<=[.!?])\s+", llm_response)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue

        # Extract citations — tolerate whitespace around colon (LLMs vary)
        pmids = re.findall(r"\[PMID:\s*(\d+)\]", sentence)
        dois = re.findall(r"\[DOI:\s*(10\.\S+?)\]", sentence)
        citations = [f"PMID:{p}" for p in pmids] + [f"DOI:{d}" for d in dois]

        # PubMed: variant (LLMs often emit this instead of PMID:)
        pubmed_ids = re.findall(r"\[PubMed:\s*(\d+)\]", sentence)
        citations.extend(f"PMID:{p}" for p in pubmed_ids)

        # Comma-separated citation brackets: [source, PubMed:111, PMID:222]
        for bracket in re.findall(r"\[([^\]]*,[^\]]*)\]", sentence):
            for m in re.finditer(r"(?:PMID|PubMed):\s*(\d+)", bracket):
                citations.append(f"PMID:{m.group(1)}")
            for m in re.finditer(r"DOI:\s*(10\.\S+?)(?:,|\s|$)", bracket):
                citations.append(f"DOI:{m.group(1)}")

        # Resolve footnote-style [N] references via the map
        footnote_refs = re.findall(r"\[(\d+)\]", sentence)
        for ref_num in footnote_refs:
            n = int(ref_num)
            if n in footnote_map:
                citations.extend(footnote_map[n])

        # Resolve ranged refs like [4-20]
        range_refs = re.findall(r"\[(\d+)-(\d+)\]", sentence)
        for start_s, end_s in range_refs:
            for n in range(int(start_s), int(end_s) + 1):
                if n in footnote_map:
                    citations.extend(footnote_map[n])

        # Deduplicate citations while preserving order
        seen: set[str] = set()
        unique_citations: list[str] = []
        for c in citations:
            if c not in seen:
                seen.add(c)
                unique_citations.append(c)
        citations = unique_citations

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
        claim_text = re.sub(r"\[PMID:\s*\d+\]", "", claim_text)
        claim_text = re.sub(r"\[PubMed:\s*\d+\]", "", claim_text)
        claim_text = re.sub(r"\[DOI:\s*10\.\S+?\]", "", claim_text)
        claim_text = re.sub(r"\[[^\]]*,\s*(?:PMID|PubMed|DOI):[^\]]*\]", "", claim_text)
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


_CANCER_FIELDS = frozenset({
    "clinical_significance", "oncogenic", "mutation_effect", "aa_mutation",
    "primary_site", "therapies", "disease_name", "variant_name",
    "evidence_level", "drug_name",
})


def _summarize_evidence(ev: dict) -> str:
    """Create a rich summary of an evidence item for the LLM prompt.

    Uses generous limits so the LLM has enough context to reason:
    - Titles: up to 300 chars
    - Abstracts: up to 800 chars (most valuable for reasoning)
    - Cancer-specific short fields: full length
    - Other descriptive fields: up to 300 chars
    """
    parts: list[str] = []

    # Title / name — generous limit
    for key in ("title", "name"):
        val = ev.get(key)
        if val:
            parts.append(str(val)[:300])

    # Abstract — most valuable content for LLM reasoning
    abstract = ev.get("abstract", "")
    if abstract:
        parts.append(f"Abstract: {str(abstract)[:800]}")

    # Cancer-specific fields — short, include fully
    for key in sorted(_CANCER_FIELDS):
        val = ev.get(key)
        if not val:
            continue
        if isinstance(val, list):
            parts.append(f"{key}: {', '.join(str(v) for v in val)}")
        else:
            parts.append(f"{key}: {val}")

    # Other descriptive fields
    for key in ("description", "product", "summary", "function"):
        val = ev.get(key)
        if val:
            parts.append(str(val)[:300])

    # Fallback: payload-level fields
    if not parts:
        payload = ev.get("payload", {})
        if isinstance(payload, dict):
            for key in ("description", "predicted_function", "summary"):
                val = payload.get(key)
                if val:
                    parts.append(str(val)[:300])
                    break

    return "; ".join(parts) if parts else str(ev)[:200]
