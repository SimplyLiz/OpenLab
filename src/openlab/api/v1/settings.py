"""LLM settings — runtime configuration for AI provider, model, and keys."""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from openlab.config import config

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    provider: str
    model: str
    anthropic_api_key_set: bool
    openai_api_key_set: bool
    ollama_url: str
    ollama_available: bool
    ollama_models: list[str]


class SettingsUpdate(BaseModel):
    provider: str | None = None
    model: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    ollama_url: str | None = None


def _ollama_status(url: str) -> tuple[bool, list[str]]:
    """Check Ollama reachability and fetch installed models in one call."""
    try:
        r = httpx.get(f"{url.rstrip('/')}/api/tags", timeout=2.0)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return True, models
        return False, []
    except Exception:
        return False, []


def _build_response() -> SettingsResponse:
    available, models = _ollama_status(config.llm.ollama_url)
    return SettingsResponse(
        provider=config.llm.provider,
        model=config.llm.model,
        anthropic_api_key_set=bool(config.llm.anthropic_api_key),
        openai_api_key_set=bool(config.llm.openai_api_key),
        ollama_url=config.llm.ollama_url,
        ollama_available=available,
        ollama_models=models,
    )


@router.get("", response_model=SettingsResponse)
def get_settings():
    return _build_response()


@router.put("", response_model=SettingsResponse)
def update_settings(body: SettingsUpdate):
    if body.provider is not None:
        config.llm.provider = body.provider
    if body.model is not None:
        config.llm.model = body.model
    if body.anthropic_api_key:
        config.llm.anthropic_api_key = body.anthropic_api_key
    if body.openai_api_key:
        config.llm.openai_api_key = body.openai_api_key
    if body.ollama_url is not None:
        config.llm.ollama_url = body.ollama_url
    return _build_response()
