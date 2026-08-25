"""Unit tests for ModelService and ModelRegistry."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest
from app.core.catalog import ModelRegistry, ModelSpec
from app.core.config import Settings
from app.core.enums import ModelName, ModelProvider
from app.services.model_service import ModelService


def test_model_registry_queries():
    """Verify ModelRegistry lookup, filtering, and validation methods."""
    all_models = ModelRegistry.get_all()
    assert len(all_models) >= 6

    gemini_flash = ModelRegistry.get(ModelName.GEMINI_3_6_FLASH.value)
    assert isinstance(gemini_flash, ModelSpec)
    assert gemini_flash.provider == ModelProvider.GEMINI

    gemini_models = ModelRegistry.get_by_provider(ModelProvider.GEMINI)
    assert len(gemini_models) == 3
    assert all(m.provider == ModelProvider.GEMINI for m in gemini_models)

    assert ModelRegistry.is_supported(ModelName.CLAUDE_3_5_SONNET.value) is True
    assert ModelRegistry.is_supported("non-existent-model") is False


@pytest.mark.asyncio
async def test_model_service_list_models_gemini_active():
    """Verify ModelService.list_models sets Gemini as active when only GEMINI_API_KEY is configured."""
    settings = Settings(
        ANTHROPIC_API_KEY="",
        OPENAI_API_KEY="",
        GEMINI_API_KEY="test-gemini-key",
        OLLAMA_MODEL="llama3.2",
    )
    service = ModelService(settings=settings)

    with patch("app.services.model_service.get_ollama_client") as mock_ollama_factory:
        mock_client = AsyncMock()
        mock_client.get.return_value = httpx.Response(200, json={"models": []})
        mock_ollama_factory.return_value = mock_client

        response = await service.list_models()
        assert response.active_model == ModelName.GEMINI_3_6_FLASH.value
        assert response.active_provider == ModelProvider.GEMINI
        assert response.providers["gemini"].configured is True


@pytest.mark.asyncio
async def test_model_service_available_models_all_operational():
    """Verify ModelService.get_available_working_models returns operational status when probes succeed."""
    settings = Settings(
        ANTHROPIC_API_KEY="test-anthropic",
        OPENAI_API_KEY="test-openai",
        GEMINI_API_KEY="test-gemini",
        OLLAMA_BASE_URL="http://localhost:11434",
    )
    service = ModelService(settings=settings)

    with patch("app.services.model_service.get_ollama_client") as mock_ollama_factory:
        mock_ollama = AsyncMock()
        mock_ollama.get.return_value = httpx.Response(200, json={"models": []})
        mock_ollama_factory.return_value = mock_ollama

        with patch("app.services.model_service.get_gemini_client") as mock_gemini_factory:
            mock_gemini = AsyncMock()
            mock_gemini.get.return_value = httpx.Response(200, json={"models": []})
            mock_gemini_factory.return_value = mock_gemini

            response = await service.get_available_working_models()
            assert response.total_working > 0
            assert response.providers["gemini"].status == "operational"
            assert response.providers["ollama"].status == "operational"
            assert response.providers["anthropic"].status == "operational"
            assert response.providers["openai"].status == "operational"
