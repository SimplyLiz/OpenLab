"""LLM service — synchronous adapter for DNASyn's DB-backed services.

This is a thin sync wrapper around the async llm_synthesis module.
DNASyn services (validation_service, etc.) call llm_service.synthesize(prompt)
synchronously. Supports Anthropic, OpenAI, Gemini, Grok, and Ollama backends.
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
                return str(models[0].get("name", ""))
    except Exception:
        pass
    return ""


def _model_for_provider(provider: str) -> str:
    """Return the right model name for the provider."""
    m: str = settings.llm_model
    cloud_markers = ("claude", "gpt", "o1-", "o3-", "gemini", "grok")
    if provider == "anthropic":
        return m if "claude" in m else "claude-sonnet-4-5-20250929"
    elif provider == "openai":
        return m if "gpt" in m or "o1" in m or "o3" in m else "gpt-4o"
    elif provider == "gemini":
        return m if "gemini" in m else "gemini-2.0-flash"
    elif provider == "grok":
        return m if "grok" in m else "grok-3-mini"
    elif provider == "ollama":
        if any(tok in m for tok in cloud_markers):
            discovered = _get_ollama_model()
            logger.info(f"Ollama auto-selected model: {discovered or 'llama3 (fallback)'}")
            return discovered or "llama3"
        return m
    return m


def _resolve_provider() -> str:
    """Pick the best available provider. Prefers ollama when running (free)."""
    preferred: str = settings.llm_provider.lower()

    # Explicit preference honored
    if preferred == "anthropic" and settings.anthropic_api_key:
        return "anthropic"
    if preferred == "openai" and settings.openai_api_key:
        return "openai"
    if preferred == "gemini" and settings.gemini_api_key:
        return "gemini"
    if preferred == "grok" and settings.grok_api_key:
        return "grok"
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
    if settings.gemini_api_key:
        return "gemini"
    if settings.grok_api_key:
        return "grok"

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
    elif provider == "gemini":
        return _gemini(prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    elif provider == "grok":
        return _grok(prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    elif provider == "ollama":
        return _ollama(prompt, purpose=purpose, gene_locus_tag=gene_locus_tag)
    else:
        raise ValueError(
            "No LLM provider available"
            " (set ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, or GROK_API_KEY)"
        )


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
    return str(data["content"][0]["text"])


def _openai_compatible(
    prompt: str,
    *,
    base_url: str,
    api_key: str,
    model: str,
    provider_name: str,
    purpose: str = "validation",
    gene_locus_tag: str | None = None,
) -> str:
    """Shared helper for OpenAI-compatible chat completion APIs (Gemini, Grok)."""
    logger.info(f"LLM synthesis via {provider_name} ({model})")
    start = time.perf_counter()
    resp = httpx.post(
        base_url,
        headers={
            "Authorization": f"Bearer {api_key}",
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
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    duration_ms = int((time.perf_counter() - start) * 1000)
    usage = data.get("usage", {})
    try:
        usage_service.record_usage(
            provider=provider_name,
            model=model,
            purpose=purpose,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            duration_ms=duration_ms,
            gene_locus_tag=gene_locus_tag,
        )
    except Exception:
        logger.debug(f"Usage logging failed for {provider_name} call", exc_info=True)
    return str(data["choices"][0]["message"]["content"])


def _gemini(
    prompt: str,
    *,
    purpose: str = "validation",
    gene_locus_tag: str | None = None,
) -> str:
    if not settings.gemini_api_key:
        raise ValueError("gemini_api_key not configured")
    return _openai_compatible(
        prompt,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        api_key=settings.gemini_api_key,
        model=_model_for_provider("gemini"),
        provider_name="gemini",
        purpose=purpose,
        gene_locus_tag=gene_locus_tag,
    )


def _grok(
    prompt: str,
    *,
    purpose: str = "validation",
    gene_locus_tag: str | None = None,
) -> str:
    if not settings.grok_api_key:
        raise ValueError("grok_api_key not configured")
    return _openai_compatible(
        prompt,
        base_url="https://api.x.ai/v1/chat/completions",
        api_key=settings.grok_api_key,
        model=_model_for_provider("grok"),
        provider_name="grok",
        purpose=purpose,
        gene_locus_tag=gene_locus_tag,
    )


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
    return str(data.get("response", ""))
