"""LLM service — synchronous adapter for DNASyn's DB-backed services.

This is a thin sync wrapper around the async llm_synthesis module.
DNASyn services (validation_service, etc.) call llm_service.synthesize(prompt)
synchronously. This module bridges that to the async providers.
"""

import logging
import time

import httpx

from openlab.config import settings
from openlab.services import usage_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a molecular biology expert specializing in minimal genomes "
    "and gene function prediction. Analyze the evidence provided and "
    "synthesize a hypothesis about the gene's function. Be specific, "
    "cite the evidence, and rate your confidence."
)


def _ollama_available() -> bool:
    """Quick check if ollama is responding."""
    try:
        resp = httpx.get(f"{settings.ollama_url}/api/tags", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def _get_ollama_model() -> str:
    """Query ollama for installed models and return the first one."""
    try:
        resp = httpx.get(f"{settings.ollama_url}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            if models:
                return models[0].get("name", "")
    except Exception:
        pass
    return ""


def _model_for_provider(provider: str) -> str:
    """Return the right model name for the provider."""
    m = settings.llm_model
    cloud_markers = ("claude", "gpt", "o1-", "o3-")
    if provider == "anthropic":
        return m if "claude" in m else "claude-sonnet-4-5-20250929"
    elif provider == "openai":
        return m if "gpt" in m or "o1" in m or "o3" in m else "gpt-4o"
    elif provider == "ollama":
        if any(tok in m for tok in cloud_markers):
            discovered = _get_ollama_model()
            logger.info(f"Ollama auto-selected model: {discovered or 'llama3 (fallback)'}")
            return discovered or "llama3"
        return m
    return m


def _resolve_provider() -> str:
    """Pick the best available provider. Prefers ollama when running (free)."""
    preferred = settings.llm_provider.lower()

    # Explicit preference honored
    if preferred == "anthropic" and settings.anthropic_api_key:
        return "anthropic"
    if preferred == "openai" and settings.openai_api_key:
        return "openai"
    if preferred == "ollama":
        return "ollama"

    # Prefer ollama if available (free, local)
    if _ollama_available():
        return "ollama"

    # Cloud fallback
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"

    return preferred


def synthesize(
    prompt: str,
    *,
    purpose: str = "validation",
    gene_locus_tag: str | None = None,
) -> str:
    """Send a prompt to the configured LLM provider and return the response text.

    Synchronous entry point for DB-backed services.
    Prefers ollama when available (free), falls back to cloud providers.
    """
    provider = _resolve_provider()
    if provider == "openai":
        return _openai(prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    elif provider == "anthropic":
        return _anthropic(prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    elif provider == "ollama":
        return _ollama(prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    else:
        raise ValueError(f"No LLM provider available (set ANTHROPIC_API_KEY, OPENAI_API_KEY, or run ollama)")


def _openai(
    prompt: str,
    *,
    purpose: str = "validation",
    gene_locus_tag: str | None = None,
) -> str:
    from openai import OpenAI

    model = _model_for_provider("openai")
    client = OpenAI(api_key=settings.openai_api_key)
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    duration_ms = int((time.perf_counter() - start) * 1000)
    usage = response.usage
    try:
        usage_service.record_usage(
            provider="openai",
            model=model,
            purpose=purpose,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            duration_ms=duration_ms,
            gene_locus_tag=gene_locus_tag,
        )
    except Exception:
        logger.debug("Usage logging failed for OpenAI call", exc_info=True)
    return response.choices[0].message.content or ""


def _anthropic(
    prompt: str,
    *,
    purpose: str = "validation",
    gene_locus_tag: str | None = None,
) -> str:
    model = _model_for_provider("anthropic")
    start = time.perf_counter()
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 2000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
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


def _ollama(
    prompt: str,
    *,
    purpose: str = "validation",
    gene_locus_tag: str | None = None,
) -> str:
    model = _model_for_provider("ollama")
    start = time.perf_counter()
    resp = httpx.post(
        f"{settings.ollama_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    duration_ms = int((time.perf_counter() - start) * 1000)
    try:
        usage_service.record_usage(
            provider="ollama",
            model=model,
            purpose=purpose,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            duration_ms=duration_ms,
            gene_locus_tag=gene_locus_tag,
        )
    except Exception:
        logger.debug("Usage logging failed for Ollama call", exc_info=True)
    return data.get("response", "")
