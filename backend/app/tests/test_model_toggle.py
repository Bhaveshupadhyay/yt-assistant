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
    assert resolve_provider_for_model("gpt-4o") == ModelProvider.OPENAI
    assert resolve_provider_for_model("gpt-4o-mini") == ModelProvider.OPENAI
    assert resolve_provider_for_model("llama3.2") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("mistral") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("qwen2.5") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("deepseek-r1") == ModelProvider.OLLAMA


def test_get_llm_client_factory_switching():
    """Verify get_llm_client instantiates correct client class based on model name."""
    settings = Settings(
        ANTHROPIC_API_KEY="test-anthropic-key",
        OPENAI_API_KEY="test-openai-key",
        OLLAMA_BASE_URL="http://localhost:11434",
    )

    client_claude = get_llm_client(model_name=ModelName.CLAUDE_3_5_SONNET, settings=settings)
    assert isinstance(client_claude, AnthropicClient)
    assert client_claude.provider == ModelProvider.ANTHROPIC

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
    mock_http_client = AsyncMock()
    mock_http_client.stream.side_effect = httpx.ConnectError("Connection refused")

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
