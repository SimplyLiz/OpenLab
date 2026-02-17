"""Evidence normalizer — extract structured terms from heterogeneous evidence payloads.

Ported from DNASyn's evidence_normalizer.py, adapted for GeneLife's
in-memory pipeline (no SQLAlchemy dependency).

Converts raw text from BLAST hits, UniProt descriptions, STRING partners, CDD
domains, InterPro matches, etc. into a controlled vocabulary of GO terms,
EC numbers, and functional categories — enabling convergence scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# EC number regex: 1.2.3.4 or partial 1.2.3.-
_EC_PATTERN = re.compile(r"\b(\d+\.\d+\.\d+\.[\d-]+)")

# GO term regex: GO:0000000
_GO_PATTERN = re.compile(r"(GO:\d{7})")

# Module-level cache
_keyword_map: dict | None = None


def reset_keyword_map_cache() -> None:
    """Reset the keyword map cache (useful in tests)."""
    global _keyword_map
    _keyword_map = None

# COG functional category letter → functional category
COG_CATEGORIES: dict[str, str] = {
    "J": "translation",
    "K": "transcription",
    "L": "dna_repair:replication",
    "D": "cell_division",
    "V": "defense",
    "T": "signal_transduction",
    "M": "membrane_biogenesis",
    "N": "cell_motility",
    "U": "transporter:secretion",
    "O": "enzyme:chaperone",
    "C": "enzyme:energy_metabolism",
    "G": "enzyme:glycolysis",
    "E": "enzyme:amino_acid_metabolism",
    "F": "enzyme:nucleotide_metabolism",
    "H": "enzyme:coenzyme_metabolism",
    "I": "enzyme:lipid_metabolism",
    "P": "transporter:ion",
    "Q": "enzyme:secondary_metabolism",
    "R": "general_function",
    "S": "unknown_function",
}


@dataclass
class NormalizedEvidence:
    """Structured representation of evidence for convergence scoring."""
    go_terms: set[str] = field(default_factory=set)
    ec_numbers: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    keywords: set[str] = field(default_factory=set)


def _load_keyword_map() -> dict:
    """Load keyword → GO mapping from YAML, cached at module level."""
    global _keyword_map
    if _keyword_map is not None:
        return _keyword_map

    # __file__ is src/openlab/services/evidence_normalizer.py
    # We need to reach the repo root's data/ directory
    map_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "go_keyword_map.yaml"
    if map_path.exists():
        _keyword_map = yaml.safe_load(map_path.read_text()) or {}
    else:
        _keyword_map = {}
    return _keyword_map


def _extract_ec_numbers(text: str) -> set[str]:
    return set(_EC_PATTERN.findall(text))


def _extract_go_terms(text: str) -> set[str]:
    return set(_GO_PATTERN.findall(text))


def _map_keywords_to_go(text: str) -> tuple[set[str], set[str]]:
    """Map keywords in text to GO terms and categories using the keyword map."""
    kw_map = _load_keyword_map()
    go_terms: set[str] = set()
    categories: set[str] = set()
    text_lower = text.lower()

    for keyword, entry in kw_map.items():
        if not isinstance(entry, dict):
            continue
        pattern = re.escape(keyword.lower())
        if re.search(r"\b" + pattern + r"\b", text_lower):
            if entry.get("go_id"):
                go_terms.add(entry["go_id"])
            if entry.get("category"):
                categories.add(entry["category"])

    return go_terms, categories


def normalize_payload(payload: dict[str, Any]) -> NormalizedEvidence:
    """Extract GO terms, EC numbers, and categories from a raw evidence dict.

    Stateless entry point for GeneLife's real-time pipeline (no DB dependency).
    """
    return _normalize_dict(payload)


def normalize_evidence(evidence_or_payload) -> NormalizedEvidence:
    """Unified normalizer — accepts either a raw dict or an ORM Evidence object.

    - dict: calls _normalize_dict directly (stateless pipeline path)
    - ORM Evidence: extracts .payload, normalizes, then validates GO terms via go_validator

    This is the dual entry point that both GeneLife and DNASyn code paths use.
    """
    if isinstance(evidence_or_payload, dict):
        return _normalize_dict(evidence_or_payload)

    # ORM Evidence object — has .payload attribute
    ev = evidence_or_payload
    result = _normalize_dict(ev.payload or {})

    # DNASyn path: validate GO terms against known-good list
    try:
        from openlab.services.go_validator import validate_go_terms
        valid_go, invalid_go = validate_go_terms(result.go_terms)
        if invalid_go:
            import logging
            logging.getLogger(__name__).warning(f"Invalid GO terms dropped: {sorted(invalid_go)}")
        result.go_terms = valid_go
    except ImportError:
        pass

    return result


def _normalize_dict(p: dict[str, Any]) -> NormalizedEvidence:
    """Core extraction logic — shared between both entry points."""
    result = NormalizedEvidence()
    p = p or {}
    text_fragments: list[str] = []

    # --- Hit descriptions (BLAST, HMMER, HHpred, Foldseek) ---
    for hit in p.get("hits", []):
        desc = hit.get("description", "")
        if desc:
            text_fragments.append(desc)
            result.ec_numbers |= _extract_ec_numbers(desc)
        name = hit.get("name", "")
        if name:
            text_fragments.append(name)
        ec = hit.get("ec_number", "")
        if ec:
            result.ec_numbers.add(ec)

    # --- InterProScan matches[] ---
    for match in p.get("matches", []):
        desc = match.get("description", "")
        if desc:
            text_fragments.append(desc)
            result.ec_numbers |= _extract_ec_numbers(desc)
        name = match.get("name", "")
        if name:
            text_fragments.append(name)
        for go in match.get("go_terms", []):
            if isinstance(go, dict):
                go_id = go.get("id", "") or go.get("term", "")
                if go_id:
                    result.go_terms.add(go_id)
            elif isinstance(go, str):
                result.go_terms |= _extract_go_terms(go)

    # --- Pfam / CDD domains ---
    for domain in p.get("domains", []):
        desc = domain.get("description", "")
        if desc:
            text_fragments.append(desc)
            result.ec_numbers |= _extract_ec_numbers(desc)
        name = domain.get("target_name", "") or domain.get("name", "")
        if name:
            text_fragments.append(name)

    # --- UniProt / protein name ---
    if p.get("protein_name"):
        text_fragments.append(p["protein_name"])
    if p.get("recommended_name"):
        text_fragments.append(p["recommended_name"])

    # --- COG / eggNOG ---
    if p.get("cog_category"):
        cog_str = p["cog_category"]
        for letter in cog_str:
            cat = COG_CATEGORIES.get(letter)
            if cat and cat not in ("general_function", "unknown_function"):
                result.categories.add(cat)
    if p.get("og_description"):
        text_fragments.append(p["og_description"])
    if p.get("description"):
        text_fragments.append(p["description"])
    if p.get("predicted_name"):
        text_fragments.append(p["predicted_name"])

    # --- EC numbers (array form) ---
    for ec in p.get("ec_numbers", []):
        if isinstance(ec, str) and ec:
            result.ec_numbers.add(ec)

    # --- GO terms (explicit in payload) ---
    for go in p.get("go_terms", []):
        if isinstance(go, dict):
            go_id = go.get("id", "") or go.get("term", "")
            if go_id:
                result.go_terms.add(go_id)
            desc = go.get("description", "")
            if desc:
                text_fragments.append(desc)
        elif isinstance(go, str):
            result.go_terms |= _extract_go_terms(go)
            parts = go.split(":")
            if len(parts) > 2:
                text_fragments.append(":".join(parts[2:]))

    if p.get("ec_number"):
        result.ec_numbers.add(p["ec_number"])

    # --- STRING partners ---
    for partner in p.get("partners", []):
        pname = partner.get("partner", "")
        if pname:
            text_fragments.append(pname)
        annotation = partner.get("annotation", "")
        if annotation:
            text_fragments.append(annotation)
        pdesc = partner.get("description", "")
        if pdesc:
            text_fragments.append(pdesc)
    if p.get("functional_description"):
        text_fragments.append(p["functional_description"])

    # --- Literature ---
    for art in p.get("articles", []):
        title = art.get("title", "")
        if title:
            text_fragments.append(title)
        abstract = art.get("abstract", "")
        if abstract:
            text_fragments.append(abstract)

    # --- Curated / predicted function ---
    if p.get("predicted_function"):
        text_fragments.append(p["predicted_function"])
    if p.get("function"):
        text_fragments.append(p["function"])

    # --- Genomic neighborhood ---
    for neighbor in p.get("neighbors", []):
        prod = neighbor.get("product", "")
        if prod:
            text_fragments.append(prod)
    if p.get("inferred_context"):
        text_fragments.append(p["inferred_context"])

    # --- Operon context ---
    for fn in p.get("operon_functions", []):
        if isinstance(fn, str) and fn:
            text_fragments.append(fn)
    if p.get("functional_context"):
        text_fragments.append(p["functional_context"])

    # --- Cancer evidence: variants, mutations, clinical significance ---
    for variant in p.get("variants", []):
        if isinstance(variant, dict):
            sig = variant.get("clinical_significance", "")
            if sig:
                text_fragments.append(sig)
            for cat in variant.get("categories", []):
                if isinstance(cat, str):
                    result.categories.add(cat)
            title = variant.get("title", "")
            if title:
                text_fragments.append(title)

    for mutation in p.get("mutations", []):
        if isinstance(mutation, dict):
            for cat in mutation.get("categories", []):
                if isinstance(cat, str):
                    result.categories.add(cat)
            aa = mutation.get("aa_mutation", "") or mutation.get("aa_change", "")
            if aa:
                text_fragments.append(aa)
            site = mutation.get("primary_site", "")
            if site:
                text_fragments.append(site)

    for entry in p.get("entries", []):
        if isinstance(entry, dict):
            for cat in entry.get("categories", []):
                if isinstance(cat, str):
                    result.categories.add(cat)
            desc = entry.get("description", "")
            if desc:
                text_fragments.append(desc)
            for therapy in entry.get("therapies", []):
                if isinstance(therapy, str) and therapy:
                    text_fragments.append(therapy)
                    result.categories.add("cancer:drug_target")

    # --- Product annotation (direct from GenBank) ---
    if p.get("product"):
        text_fragments.append(p["product"])

    # --- Topology / localization ---
    if p.get("topology"):
        text_fragments.append(p["topology"])
    if p.get("target"):
        text_fragments.append(p["target"])

    # Combine and extract structured terms
    combined_text = " ".join(text_fragments)
    result.go_terms |= _extract_go_terms(combined_text)
    result.ec_numbers |= _extract_ec_numbers(combined_text)

    mapped_go, mapped_cats = _map_keywords_to_go(combined_text)
    result.go_terms |= mapped_go
    result.categories |= mapped_cats

    # Extract raw keywords (lower-cased, deduplicated) — unigrams + bigrams
    for fragment in text_fragments:
        words = fragment.lower().split()
        filtered = [w for w in words if len(w) > 3 and w not in _STOP_WORDS]
        result.keywords |= set(filtered)
        for i in range(len(filtered) - 1):
            result.keywords.add(f"{filtered[i]} {filtered[i+1]}")

    return result


# Common English stop words + bioinformatics noise words
_STOP_WORDS = {
    "the", "and", "for", "with", "from", "this", "that", "have", "been",
    "will", "more", "than", "also", "into", "when", "over", "such", "each",
    "only", "which", "their", "there", "about", "some", "would", "could",
    "other", "most", "very", "like", "just", "well", "protein", "gene",
    "function", "putative", "hypothetical", "uncharacterized", "predicted",
    "probable", "possible", "domain", "family", "superfamily", "subfamily",
    "homolog", "homologue", "similar", "related", "conserved", "unknown",
    "containing", "involved", "associated", "required", "encoding",
    "subunit", "binding", "activity", "component", "dependent", "type",
    "class", "specific", "terminal", "chain", "system", "complex",
    "essential", "inner", "outer", "small", "large",
}
