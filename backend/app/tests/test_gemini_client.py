"""Unit and integration tests for Google Gemini LLM client implementation."""

import json
from typing import Any
import httpx
import pytest
from app.core.config import Settings
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import ModelProviderException
from app.services.llm.factory import get_llm_client, resolve_provider_for_model
from app.services.llm.gemini_client import GeminiClient


@pytest.mark.asyncio
async def test_gemini_client_missing_key_raises() -> None:
    """Test GeminiClient raises ModelProviderException when API key is missing."""
    client = GeminiClient(api_key=None, settings=Settings(GEMINI_API_KEY=None))
    assert await client.check_health() is False
    with pytest.raises(ModelProviderException, match="Gemini API key is not configured"):
        async for _ in client.astream(messages=[{"role": "user", "content": "Hi"}]):
            pass


@pytest.mark.asyncio
async def test_gemini_client_streaming_success() -> None:
    """Test GeminiClient successfully parses Google Gemini SSE data chunks."""
    sse_lines = [
        'data: {"candidates": [{"content": {"parts": [{"text": "Growth "}], "role": "model"}}]}\n\n',
        'data: {"candidates": [{"content": {"parts": [{"text": "Loops"}], "role": "model"}, "finishReason": "STOP"}]}\n\n',
    ]
    raw_response = "".join(sse_lines).encode("utf-8")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "streamGenerateContent?alt=sse" in str(request.url)
        assert request.headers.get("x-goog-api-key") == "test-gemini-key"
        body = json.loads(request.content.decode("utf-8"))
        assert "contents" in body
        assert body["contents"][0]["role"] == "user"
        assert body["contents"][0]["parts"][0]["text"] == "Explain retention"
        assert body["systemInstruction"]["parts"][0]["text"] == "You are Lenny Assistant"
        return httpx.Response(200, content=raw_response, headers={"content-type": "text/event-stream"})

    mock_transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://generativelanguage.googleapis.com/v1beta") as http_client:
        client = GeminiClient(
            model_name=ModelName.GEMINI_3_6_FLASH,
            api_key="test-gemini-key",
            http_client=http_client,
        )
        assert await client.check_health() is True

        tokens = []
        async for tok in client.astream(
            messages=[{"role": "user", "content": "Explain retention"}],
            system_prompt="You are Lenny Assistant",
        ):
            tokens.append(tok)

        assert "".join(tokens) == "Growth Loops"


@pytest.mark.asyncio
async def test_gemini_client_acomplete() -> None:
    """Test GeminiClient.acomplete() aggregates streamed tokens."""
    sse_lines = [
        'data: {"candidates": [{"content": {"parts": [{"text": "B2B "}], "role": "model"}}]}\n\n',
        'data: {"candidates": [{"content": {"parts": [{"text": "SaaS"}], "role": "model"}}]}\n\n',
    ]
    raw_response = "".join(sse_lines).encode("utf-8")

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=raw_response, headers={"content-type": "text/event-stream"})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://generativelanguage.googleapis.com/v1beta") as http_client:
        client = GeminiClient(
            model_name=ModelName.GEMINI_3_7_PRO,
            api_key="test-key",
            http_client=http_client,
        )
        result = await client.acomplete(messages=[{"role": "user", "content": "Hello"}])
        assert result == "B2B SaaS"


@pytest.mark.asyncio
async def test_gemini_client_http_error_handling() -> None:
    """Test GeminiClient raises ModelProviderException on upstream 400/403/500 errors."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(403, json={"error": {"message": "API key invalid", "code": 403}})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://generativelanguage.googleapis.com/v1beta") as http_client:
        client = GeminiClient(
            model_name=ModelName.GEMINI_3_6_FLASH,
            api_key="invalid-key",
            http_client=http_client,
        )
        with pytest.raises(ModelProviderException, match="Gemini API returned status 403"):
            async for _ in client.astream(messages=[{"role": "user", "content": "Hello"}]):
                pass


@pytest.mark.asyncio
async def test_gemini_client_stream_error_payload() -> None:
    """Test GeminiClient raises ModelProviderException when stream emits an error object."""
    sse_lines = [
        'data: {"error": {"message": "Quota exceeded for model gemini-3.6-flash"}}\n\n',
    ]
    raw_response = "".join(sse_lines).encode("utf-8")

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=raw_response, headers={"content-type": "text/event-stream"})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://generativelanguage.googleapis.com/v1beta") as http_client:
        client = GeminiClient(
            model_name=ModelName.GEMINI_3_6_FLASH,
            api_key="test-key",
            http_client=http_client,
        )
        with pytest.raises(ModelProviderException, match="Quota exceeded"):
            async for _ in client.astream(messages=[{"role": "user", "content": "Hello"}]):
                pass


def test_gemini_factory_routing() -> None:
    """Test factory router correctly identifies and instantiates GeminiClient."""
    assert resolve_provider_for_model("gemini-3.6-flash") == ModelProvider.GEMINI
    assert resolve_provider_for_model("gemini-3.6-flash-lite") == ModelProvider.GEMINI
    assert resolve_provider_for_model("gemini-3.7-pro") == ModelProvider.GEMINI

    test_settings = Settings(
        GEMINI_API_KEY="test-gemini-key",
        ANTHROPIC_API_KEY=None,
        OPENAI_API_KEY=None,
    )
    client = get_llm_client("gemini-3.6-flash", settings=test_settings)
    assert isinstance(client, GeminiClient)
    assert client.provider == ModelProvider.GEMINI
    assert client.model_name == "gemini-3.6-flash"
