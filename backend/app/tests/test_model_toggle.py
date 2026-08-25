"""Automated pytest suite for model toggling & provider switching (Task 5.2)."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest
from httpx import AsyncClient
from app.core.config import Settings
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import OllamaUnavailableException
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.factory import get_llm_client, resolve_provider_for_model
from app.services.llm.ollama_client import OllamaClient
from app.services.llm.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_list_models_endpoint_structure(async_client: AsyncClient):
    """Verify GET /api/v1/models returns active model and toggleable model catalog."""
    with patch("app.api.v1.models.get_ollama_client") as mock_ollama_factory:
        mock_client = AsyncMock()
        mock_client.get.return_value = httpx.Response(200, json={"models": []})
        mock_ollama_factory.return_value = mock_client

        response = await async_client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()

        assert "active_model" in data
        assert "active_provider" in data
        assert "available_models" in data
        assert len(data["available_models"]) >= 6

        # Verify cloud vs local models
        claude_model = next((m for m in data["available_models"] if m["id"] == ModelName.CLAUDE_3_5_SONNET.value), None)
        assert claude_model is not None
        assert claude_model["is_cloud"] is True

        llama_model = next((m for m in data["available_models"] if m["id"] == ModelName.LLAMA_3_2.value), None)
        assert llama_model is not None
        assert llama_model["is_cloud"] is False
        assert llama_model["is_available"] is True  # because mocked 200


def test_resolve_provider_for_model():
    """Verify correct provider mapping for various model families."""
    assert resolve_provider_for_model("claude-3-5-sonnet") == ModelProvider.ANTHROPIC
    assert resolve_provider_for_model("claude-3-7-sonnet") == ModelProvider.ANTHROPIC
    assert resolve_provider_for_model("gemini-2.0-flash") == ModelProvider.GEMINI
    assert resolve_provider_for_model("gemini-1.5-pro") == ModelProvider.GEMINI
    assert resolve_provider_for_model("gpt-4o") == ModelProvider.OPENAI
    assert resolve_provider_for_model("gpt-4o-mini") == ModelProvider.OPENAI
    assert resolve_provider_for_model("llama3.2") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("mistral") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("qwen2.5") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("deepseek-r1") == ModelProvider.OLLAMA


def test_get_llm_client_factory_switching():
    """Verify get_llm_client instantiates correct client class based on model name."""
    from app.services.llm.gemini_client import GeminiClient

    settings = Settings(
        ANTHROPIC_API_KEY="test-anthropic-key",
        OPENAI_API_KEY="test-openai-key",
        GEMINI_API_KEY="test-gemini-key",
        OLLAMA_MODEL="llama3.2",
    )

    client_claude = get_llm_client(model_name=ModelName.CLAUDE_3_5_SONNET, settings=settings)
    assert isinstance(client_claude, AnthropicClient)
    assert client_claude.provider == ModelProvider.ANTHROPIC

    client_gemini = get_llm_client(model_name=ModelName.GEMINI_2_0_FLASH, settings=settings)
    assert isinstance(client_gemini, GeminiClient)
    assert client_gemini.provider == ModelProvider.GEMINI

    client_openai = get_llm_client(model_name=ModelName.GPT_4O, settings=settings)
    assert isinstance(client_openai, OpenAIClient)
    assert client_openai.provider == ModelProvider.OPENAI

    client_llama = get_llm_client(model_name=ModelName.LLAMA_3_2, settings=settings)
    assert isinstance(client_llama, OllamaClient)
    assert client_llama.provider == ModelProvider.OLLAMA


@pytest.mark.asyncio
async def test_ollama_offline_raises_service_unavailable():
    """Verify that when Ollama is offline, OllamaClient raises OllamaUnavailableException (503)."""
    settings = Settings(OLLAMA_BASE_URL="http://localhost:59999")  # Unused port
    from unittest.mock import MagicMock
    mock_http_client = MagicMock(spec=httpx.AsyncClient)
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__.side_effect = httpx.ConnectError("Connection refused")
    mock_stream_ctx.__aexit__.return_value = None
    mock_http_client.stream.return_value = mock_stream_ctx

    client = OllamaClient(
        model_name=ModelName.LLAMA_3_2,
        settings=settings,
        http_client=mock_http_client,
    )

    with pytest.raises(OllamaUnavailableException) as exc_info:
        async for _ in client.astream(messages=[{"role": "user", "content": "Hello"}]):
            pass

    assert exc_info.value.status_code == 503
    assert "Ollama daemon is unreachable" in exc_info.value.message


@pytest.mark.asyncio
async def test_list_available_working_models_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/models/available returns verified operational models."""
    with patch("app.api.v1.models.get_ollama_client") as mock_ollama_factory:
        mock_ollama = AsyncMock()
        mock_ollama.get.return_value = httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})
        mock_ollama_factory.return_value = mock_ollama

        with patch("app.api.v1.models.get_gemini_client") as mock_gemini_factory:
            mock_gemini = AsyncMock()
            mock_gemini.get.return_value = httpx.Response(200, json={"models": []})
            mock_gemini_factory.return_value = mock_gemini

            response = await async_client.get("/api/v1/models/available")
            assert response.status_code == 200
            data = response.json()

            assert "total_working" in data
            assert "working_models" in data
            assert "providers" in data
            assert data["total_working"] >= 1
            assert len(data["working_models"]) == data["total_working"]

            # Test alias endpoint /models/working
            alias_response = await async_client.get("/api/v1/models/working")
            assert alias_response.status_code == 200
            assert alias_response.json()["total_working"] == data["total_working"]
