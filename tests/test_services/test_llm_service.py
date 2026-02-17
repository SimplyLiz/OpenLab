"""Tests for LLM service."""

from unittest.mock import patch, MagicMock

import pytest


def test_synthesize_openai():
    pytest.importorskip("openai")
    with patch("openlab.services.llm_service.settings") as mock_settings:
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_settings.llm_model = "gpt-4o"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This gene likely encodes a transporter."
        mock_client.chat.completions.create.return_value = mock_response

        with patch("openai.OpenAI", return_value=mock_client):
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


def test_synthesize_unknown_provider():
    with patch("openlab.services.llm_service.settings") as mock_settings:
        mock_settings.llm_provider = "invalid"

        from openlab.services.llm_service import synthesize

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            synthesize("test")
