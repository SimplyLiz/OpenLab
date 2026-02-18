"""Tests for LLM service."""

import sys
from unittest.mock import MagicMock, patch

import pytest


def test_synthesize_openai():
    mock_openai_mod = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This gene likely encodes a transporter."
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_mod.OpenAI.return_value = mock_client

    with (
        patch.dict(sys.modules, {"openai": mock_openai_mod}),
        patch("openlab.services.llm_service.settings") as mock_settings,
    ):
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_settings.llm_model = "gpt-4o"

        from openlab.services.llm_service import synthesize

        result = synthesize("What does this gene do?")
        assert "transporter" in result
        mock_client.chat.completions.create.assert_called_once()


def test_synthesize_ollama():
    with patch("openlab.services.llm_service.settings") as mock_settings:
        mock_settings.llm_provider = "ollama"
        mock_settings.ollama_url = "http://localhost:11434"
        mock_settings.llm_model = "llama3"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Predicted membrane protein."}
        mock_resp.raise_for_status = MagicMock()

        with patch("openlab.services.llm_service.httpx.post", return_value=mock_resp):
            from openlab.services.llm_service import synthesize

            result = synthesize("Analyze this gene")
            assert "membrane" in result


def test_synthesize_anthropic():
    with patch("openlab.services.llm_service.settings") as mock_settings:
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.llm_model = "claude-sonnet-4-5-20250929"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"text": "This is an ATPase subunit."}]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("openlab.services.llm_service.httpx.post", return_value=mock_resp):
            from openlab.services.llm_service import synthesize

            result = synthesize("Analyze gene")
            assert "ATPase" in result


def test_synthesize_gemini():
    with patch("openlab.services.llm_service.settings") as mock_settings:
        mock_settings.llm_provider = "gemini"
        mock_settings.gemini_api_key = "test-gemini-key"
        mock_settings.llm_model = "gemini-2.0-flash"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Kinase domain detected."}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("openlab.services.llm_service.httpx.post", return_value=mock_resp) as mock_post:
            from openlab.services.llm_service import synthesize

            result = synthesize("Analyze gene")
            assert "Kinase" in result
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "generativelanguage.googleapis.com" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-gemini-key"


def test_synthesize_grok():
    with patch("openlab.services.llm_service.settings") as mock_settings:
        mock_settings.llm_provider = "grok"
        mock_settings.grok_api_key = "test-grok-key"
        mock_settings.llm_model = "grok-3-mini"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Tumor suppressor activity."}}],
            "usage": {"prompt_tokens": 40, "completion_tokens": 15},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("openlab.services.llm_service.httpx.post", return_value=mock_resp) as mock_post:
            from openlab.services.llm_service import synthesize

            result = synthesize("Analyze gene")
            assert "Tumor suppressor" in result
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "api.x.ai" in call_args[0][0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-grok-key"


def test_synthesize_unknown_provider():
    with patch("openlab.services.llm_service.settings") as mock_settings:
        mock_settings.llm_provider = "invalid"
        mock_settings.anthropic_api_key = ""
        mock_settings.openai_api_key = ""
        mock_settings.gemini_api_key = ""
        mock_settings.grok_api_key = ""
        mock_settings.ollama_url = "http://localhost:99999"

        from openlab.services.llm_service import synthesize

        with pytest.raises(ValueError, match="No LLM provider available"):
            synthesize("test")
