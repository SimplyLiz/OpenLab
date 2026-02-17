"""Find the Methods section in extracted paper text.

Uses regex patterns first (fast, reliable for standard headings).
Falls back to LLM-based extraction for non-standard formats.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Common Methods section headings (case-insensitive)
_METHODS_PATTERNS = [
    r"(?i)^#+\s*(?:materials?\s+and\s+)?methods?\s*$",
    r"(?i)^#+\s*experimental\s+(?:procedures?|methods?|section)\s*$",
    r"(?i)^#+\s*(?:supplementary\s+)?methods?\s+(?:and\s+materials?)?\s*$",
    r"(?i)^#+\s*(?:online\s+)?methods?\s*$",
    r"(?i)^#+\s*(?:star\s+)?methods?\s*$",
    r"(?i)^(?:materials?\s+and\s+)?methods?\s*$",
    r"(?i)^experimental\s+procedures?\s*$",
]

# Section headings that mark the END of the methods section
_END_PATTERNS = [
    r"(?i)^#+\s*results?\s*$",
    r"(?i)^#+\s*discussion\s*$",
    r"(?i)^#+\s*acknowledgement?s?\s*$",
    r"(?i)^#+\s*references?\s*$",
    r"(?i)^#+\s*supplementary\s*$",
    r"(?i)^#+\s*data\s+availability\s*$",
    r"(?i)^#+\s*author\s+contributions?\s*$",
    r"(?i)^#+\s*competing\s+interests?\s*$",
    r"(?i)^#+\s*funding\s*$",
    r"(?i)^results?\s*$",
    r"(?i)^discussion\s*$",
    r"(?i)^references?\s*$",
]


def find_methods_section(text: str) -> str:
    """Extract the Methods section from paper text.

    Returns the methods text, or empty string if not found.
    """
    result = _find_by_regex(text)
    if result:
        return result

    # If regex fails, try a more lenient approach
    result = _find_by_keywords(text)
    if result:
        return result

    logger.warning("Could not identify Methods section")
    return ""


def _find_by_regex(text: str) -> str:
    """Find Methods section using heading pattern matching."""
    lines = text.split("\n")
    start_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        if start_idx is None:
            for pattern in _METHODS_PATTERNS:
                if re.match(pattern, stripped):
                    start_idx = i + 1
                    break
        else:
            for pattern in _END_PATTERNS:
                if re.match(pattern, stripped):
                    methods_text = "\n".join(lines[start_idx:i])
                    if methods_text.strip():
                        return methods_text.strip()

    # If we found a start but no end, take everything after
    if start_idx is not None:
        methods_text = "\n".join(lines[start_idx:])
        if methods_text.strip():
            return methods_text.strip()

    return ""


def _find_by_keywords(text: str) -> str:
    """Fallback: find a contiguous block that mentions common methods keywords."""
    methods_keywords = [
        "pcr", "amplification", "sequencing", "library preparation",
        "cell culture", "transfection", "western blot", "rna extraction",
        "dna extraction", "incubated", "centrifuged", "resuspended",
        "protocol", "performed according", "manufacturer's instructions",
    ]

    paragraphs = text.split("\n\n")
    methods_paras = []
    in_methods = False

    for para in paragraphs:
        para_lower = para.lower()
        keyword_count = sum(1 for kw in methods_keywords if kw in para_lower)

        if keyword_count >= 2:
            in_methods = True
            methods_paras.append(para)
        elif in_methods and keyword_count >= 1:
            methods_paras.append(para)
        elif in_methods and keyword_count == 0:
            # Potentially left the methods section
            if len(methods_paras) > 2:
                break
            in_methods = False
            methods_paras = []

    if methods_paras:
        return "\n\n".join(methods_paras).strip()

    return ""
