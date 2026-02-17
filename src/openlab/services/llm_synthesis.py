"""LLM synthesis service — multi-provider adapter for hypothesis generation.

Ported from DNASyn's llm_service.py, made fully async with httpx.
Supports Anthropic, OpenAI, and Ollama backends.

Takes collected evidence for a mystery gene and synthesizes a
human-readable hypothesis about its function.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from openlab.config import config
from openlab.services import usage_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a molecular biology expert specializing in minimal synthetic genomes "
    "(JCVI-syn1.0, syn2.0, syn3.0, syn3A) and gene function prediction. "
    "Analyze the evidence provided and synthesize a hypothesis about the gene's function. "
    "Be specific, cite the evidence sources, and rate your confidence (0.0-1.0). "
    "Structure your response as:\n"
    "1. **Predicted function**: <concise function description>\n"
    "2. **Evidence summary**: <key evidence points>\n"
    "3. **Confidence**: <0.0-1.0 with reasoning>\n"
    "4. **Category**: <one of: gene_expression, cell_membrane, metabolism, "
    "genome_preservation, regulatory, unknown>"
)


def build_evidence_prompt(
    locus_tag: str,
    product: str,
    protein_length: int,
    evidence_list: list[dict[str, Any]],
    convergence_score: float,
) -> str:
    """Build a synthesis prompt from collected evidence."""
    lines = [
        f"Gene: {locus_tag}",
        f"Current annotation: {product or 'hypothetical protein'}",
        f"Protein length: {protein_length} aa",
        f"Evidence convergence score: {convergence_score:.3f}",
        "",
        "Evidence collected from independent sources:",
        "",
    ]

    for i, ev in enumerate(evidence_list, 1):
        source = ev.get("source", "unknown")
        lines.append(f"--- Evidence {i} (source: {source}) ---")

        # Format key payload fields
        for key, value in ev.items():
            if key == "source":
                continue
            if isinstance(value, list) and value:
                if isinstance(value[0], dict):
                    for item in value[:5]:
                        desc = item.get("description", "") or item.get("name", "")
                        if desc:
                            lines.append(f"  {key}: {desc}")
                else:
                    lines.append(f"  {key}: {', '.join(str(v) for v in value[:10])}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"  {key}.{k}: {v}")
            elif value:
                lines.append(f"  {key}: {value}")
        lines.append("")

    lines.append(
        "Based on ALL evidence above, what is the most likely function of this gene? "
        "Consider the convergence across independent sources."
    )

    return "\n".join(lines)


async def synthesize(
    http: httpx.AsyncClient,
    prompt: str,
    *,
    purpose: str = "gene_synthesis",
    gene_locus_tag: str | None = None,
) -> str:
    """Send a prompt to the configured LLM provider and return the response.

    Provider selection:
    - If ollama is reachable, use it (free, local, fast for routine tasks)
    - Otherwise fall back to configured cloud provider
    """
    provider = _resolve_provider()
    if provider == "anthropic":
        return await _anthropic(http, prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    elif provider == "openai":
        return await _openai(http, prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    elif provider == "ollama":
        return await _ollama(http, prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    else:
        raise ValueError(f"No LLM provider available (set ANTHROPIC_API_KEY or OPENAI_API_KEY)")


def _ollama_available() -> bool:
    """Quick check if ollama is responding."""
    try:
        resp = httpx.get(f"{config.llm.ollama_url}/api/tags", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def _resolve_provider() -> str:
    """Pick the best available provider based on config + available keys.

    Strategy: prefer ollama when available (free, local), fall back to cloud.
    """
    preferred = config.llm.provider.lower()

    # Explicit preference is always honored
    if preferred == "anthropic" and config.llm.anthropic_api_key:
        return "anthropic"
    if preferred == "openai" and config.llm.openai_api_key:
        return "openai"
    if preferred == "ollama":
        return "ollama"

    # If ollama is running locally, prefer it (free)
    if _ollama_available():
        return "ollama"

    # Fallback: use whichever cloud key is available
    if config.llm.anthropic_api_key:
        return "anthropic"
    if config.llm.openai_api_key:
        return "openai"

    return preferred  # will fail with a clear error in the provider func


def extract_confidence(response: str) -> float:
    """Extract confidence score from LLM response."""
    patterns = [
        r"[Cc]onfidence[:\s*]+(\d+\.?\d*)",
        r"[Cc]onfidence[:\s*]+\*?\*?(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*/\s*1\.0",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            try:
                score = float(match.group(1))
                if score > 1.0:
                    score = score / 100.0  # handle "75%" style
                return round(max(0.0, min(1.0, score)), 2)
            except ValueError:
                continue
    return 0.3  # default if not parseable


def extract_predicted_function(response: str) -> str:
    """Extract the predicted function from an LLM response."""
    patterns = [
        r"1\.\s*\*{0,2}[Pp]redicted\s+[Ff]unction\**[:\s*]+(.+?)(?:\n|$)",
        r"\*{0,2}[Pp]redicted\s+[Ff]unction\**[:\s*]+(.+?)(?:\n|$)",
        r"\*{0,2}[Mm]ost\s+likely\s+function\**[:\s*]+(.+?)(?:\n|$)",
        r"1\.\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            text = match.group(1).strip().strip("*").strip()
            # Remove locus tag prefixes
            text = re.sub(r"^JCVISYN3?A?_\d+\s+", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^[Tt]he\s+gene\s+\S+\s+", "", text)
            if text:
                return text[:200]
    # Fallback: first non-empty line
    for line in response.strip().split("\n"):
        line = line.strip().lstrip("*#-").strip()
        if line and len(line) > 10:
            return line[:200]
    return ""


def extract_category(response: str) -> str:
    """Extract the suggested category from an LLM response."""
    pattern = r"[Cc]ategory[:\s*]+\*?\*?(\w[\w_\s]*)"
    match = re.search(pattern, response)
    if match:
        cat = match.group(1).strip().lower().replace(" ", "_")
        valid = {"gene_expression", "cell_membrane", "metabolism",
                 "genome_preservation", "regulatory", "unknown"}
        if cat in valid:
            return cat
    return ""


# --- Provider implementations ---


def _get_ollama_model() -> str:
    """Query ollama for installed models and return the first one."""
    try:
        resp = httpx.get(f"{config.llm.ollama_url}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            if models:
                return models[0].get("name", "")
    except Exception:
        pass
    return ""


def _is_cloud_model(name: str) -> bool:
    """Check if a model name belongs to a cloud provider, not ollama."""
    return any(tok in name for tok in ("claude", "gpt", "o1-", "o3-"))


def _model_for_provider(provider: str) -> str:
    """Return the model to use, applying sensible defaults per provider.

    If the user explicitly configured a model that matches the provider, use it.
    Otherwise fall back to a good default for that provider.
    """
    m = config.llm.model
    if provider == "anthropic":
        return m if "claude" in m else "claude-sonnet-4-5-20250929"
    elif provider == "openai":
        return m if "gpt" in m or "o1" in m or "o3" in m else "gpt-4o"
    elif provider == "ollama":
        if _is_cloud_model(m):
            discovered = _get_ollama_model()
            logger.info(f"Ollama auto-selected model: {discovered or 'llama3 (fallback)'}")
            return discovered or "llama3"
        return m
    return m


async def _anthropic(
    http: httpx.AsyncClient,
    prompt: str,
    *,
    purpose: str = "gene_synthesis",
    gene_locus_tag: str | None = None,
) -> str:
    if not config.llm.anthropic_api_key:
        raise ValueError("anthropic_api_key not configured")
    model = _model_for_provider("anthropic")
    logger.info(f"LLM synthesis via Anthropic ({model})")
    start = time.perf_counter()
    resp = await http.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.llm.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    duration_ms = int((time.perf_counter() - start) * 1000)
    usage = data.get("usage", {})
    try:
        usage_service.record_usage(
            provider="anthropic",
            model=model,
            purpose=purpose,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            duration_ms=duration_ms,
            gene_locus_tag=gene_locus_tag,
        )
    except Exception:
        logger.debug("Usage logging failed for Anthropic call", exc_info=True)
    return data["content"][0]["text"]


async def _openai(
    http: httpx.AsyncClient,
    prompt: str,
    *,
    purpose: str = "gene_synthesis",
    gene_locus_tag: str | None = None,
) -> str:
    if not config.llm.openai_api_key:
        raise ValueError("openai_api_key not configured")
    model = _model_for_provider("openai")
    logger.info(f"LLM synthesis via OpenAI ({model})")
    start = time.perf_counter()
    resp = await http.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config.llm.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    duration_ms = int((time.perf_counter() - start) * 1000)
    usage = data.get("usage", {})
    try:
        usage_service.record_usage(
            provider="openai",
            model=model,
            purpose=purpose,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            duration_ms=duration_ms,
            gene_locus_tag=gene_locus_tag,
        )
    except Exception:
        logger.debug("Usage logging failed for OpenAI call", exc_info=True)
    return data["choices"][0]["message"]["content"]


async def _ollama(
    http: httpx.AsyncClient,
    prompt: str,
    *,
    purpose: str = "gene_synthesis",
    gene_locus_tag: str | None = None,
) -> str:
    start = time.perf_counter()
    resp = await http.post(
        f"{config.llm.ollama_url}/api/generate",
        json={
            "model": config.llm.model,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
        },
        timeout=300.0,
    )
    resp.raise_for_status()
    data = resp.json()
    duration_ms = int((time.perf_counter() - start) * 1000)
    try:
        usage_service.record_usage(
            provider="ollama",
            model=config.llm.model,
            purpose=purpose,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            duration_ms=duration_ms,
            gene_locus_tag=gene_locus_tag,
        )
    except Exception:
        logger.debug("Usage logging failed for Ollama call", exc_info=True)
    return data.get("response", "")
