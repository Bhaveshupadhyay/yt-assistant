"""Unit and integration tests for LLM provider abstraction layer."""

from collections.abc import AsyncIterator
import json
from typing import Any
import httpx
import pytest
from app.core.config import Settings
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import ModelProviderException, OllamaUnavailableException
from app.services.llm import (
    AnthropicClient,
    BaseLLMClient,
    OllamaClient,
    OpenAIClient,
    get_llm_client,
    resolve_provider_for_model,
)


class MockLLMClient(BaseLLMClient):
    """Mock implementation of BaseLLMClient for testing."""

    def __init__(self, responses: list[str] | None = None) -> None:
        super().__init__(
            model_name="mock-model",
            provider=ModelProvider.ANTHROPIC,
        )
        self.responses = responses or ["Mocked", " response", " tokens."]
        self.healthy = True

    async def astream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        for r in self.responses:
            yield r

    async def check_health(self) -> bool:
        return self.healthy


@pytest.mark.asyncio
async def test_base_llm_client_acomplete() -> None:
    """Test BaseLLMClient.acomplete() properly aggregates token chunks from astream()."""
    client = MockLLMClient(responses=["Hello", " ", "World", "!"])
    result = await client.acomplete(messages=[{"role": "user", "content": "Hi"}], system_prompt="Test")
    assert result == "Hello World!"


@pytest.mark.asyncio
async def test_base_llm_client_astream_chat_alias() -> None:
    """Test BaseLLMClient.astream_chat() alias operates identically to astream()."""
    client = MockLLMClient(responses=["Token1", "Token2"])
    tokens = []
    async for t in client.astream_chat(messages=[{"role": "user", "content": "Hi"}]):
        tokens.append(t)
    assert tokens == ["Token1", "Token2"]


def test_resolve_provider_for_model() -> None:
    """Test provider resolution based on model name strings."""
    assert resolve_provider_for_model("claude-3-5-sonnet") == ModelProvider.ANTHROPIC
    assert resolve_provider_for_model("claude-3-7-sonnet") == ModelProvider.ANTHROPIC
    assert resolve_provider_for_model("gpt-4o") == ModelProvider.OPENAI
    assert resolve_provider_for_model("gpt-4o-mini") == ModelProvider.OPENAI
    assert resolve_provider_for_model("llama3.2") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("mistral:7b") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("qwen2.5:7b") == ModelProvider.OLLAMA
    assert resolve_provider_for_model("deepseek-r1") == ModelProvider.OLLAMA


def test_get_llm_client_factory() -> None:
    """Test get_llm_client properly instantiates corresponding client subclasses."""
    test_settings = Settings(
        ANTHROPIC_API_KEY="sk-ant-test",
        OPENAI_API_KEY="sk-test",
        OLLAMA_MODEL="llama3.2",
    )

    client_claude = get_llm_client("claude-3-5-sonnet", settings=test_settings)
    assert isinstance(client_claude, AnthropicClient)
    assert client_claude.provider == ModelProvider.ANTHROPIC

    client_openai = get_llm_client("gpt-4o", settings=test_settings)
    assert isinstance(client_openai, OpenAIClient)
    assert client_openai.provider == ModelProvider.OPENAI

    client_ollama = get_llm_client("llama3.2", settings=test_settings)
    assert isinstance(client_ollama, OllamaClient)
    assert client_ollama.provider == ModelProvider.OLLAMA

    # Explicit provider override
    override_client = get_llm_client("custom-model", provider=ModelProvider.ANTHROPIC, settings=test_settings)
    assert isinstance(override_client, AnthropicClient)


# ==========================================
# Anthropic Client Tests
# ==========================================
@pytest.mark.asyncio
async def test_anthropic_client_missing_key_raises() -> None:
    """Test AnthropicClient raises ModelProviderException when API key is missing."""
    client = AnthropicClient(api_key=None, settings=Settings(ANTHROPIC_API_KEY=None))
    assert await client.check_health() is False
    with pytest.raises(ModelProviderException, match="API key is not configured"):
        async for _ in client.astream(messages=[{"role": "user", "content": "Hi"}]):
            pass


@pytest.mark.asyncio
async def test_anthropic_client_streaming_success() -> None:
    """Test AnthropicClient successfully parses SSE content_block_delta chunks."""
    sse_lines = [
        'event: message_start\ndata: {"type": "message_start"}\n\n',
        'event: content_block_delta\ndata: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Elena "}}\n\n',
        'event: content_block_delta\ndata: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Verna"}}\n\n',
        'event: message_stop\ndata: {"type": "message_stop"}\n\n',
    ]
    raw_response = "".join(sse_lines).encode("utf-8")

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=raw_response, headers={"content-type": "text/event-stream"})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://api.anthropic.com") as http_client:
        client = AnthropicClient(
            model_name=ModelName.CLAUDE_3_5_SONNET,
            api_key="sk-ant-test-123",
            http_client=http_client,
        )
        assert await client.check_health() is True

        tokens = []
        async for tok in client.astream(
            messages=[{"role": "user", "content": "Tell me about PLG"}],
            system_prompt="You are Lenny Assistant",
        ):
            tokens.append(tok)

        assert "".join(tokens) == "Elena Verna"


@pytest.mark.asyncio
async def test_anthropic_client_http_error_handling() -> None:
    """Test AnthropicClient raises ModelProviderException on upstream 401/500 errors."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(401, json={"error": {"message": "Invalid API key"}})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://api.anthropic.com") as http_client:
        client = AnthropicClient(
            api_key="bad-key",
            http_client=http_client,
        )
        with pytest.raises(ModelProviderException, match="Anthropic API returned status 401"):
            async for _ in client.astream(messages=[{"role": "user", "content": "Hi"}]):
                pass


# ==========================================
# OpenAI Client Tests
# ==========================================
@pytest.mark.asyncio
async def test_openai_client_missing_key_raises() -> None:
    """Test OpenAIClient raises ModelProviderException when API key is missing."""
    client = OpenAIClient(api_key=None, settings=Settings(OPENAI_API_KEY=None))
    assert await client.check_health() is False
    with pytest.raises(ModelProviderException, match="API key is not configured"):
        async for _ in client.astream(messages=[{"role": "user", "content": "Hi"}]):
            pass


@pytest.mark.asyncio
async def test_openai_client_streaming_success() -> None:
    """Test OpenAIClient parses chat completions SSE stream."""
    sse_lines = [
        'data: {"choices": [{"delta": {"content": "Shreyas "}}]}\n\n',
        'data: {"choices": [{"delta": {"content": "Doshi"}}]}\n\n',
        "data: [DONE]\n\n",
    ]
    raw_response = "".join(sse_lines).encode("utf-8")

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=raw_response, headers={"content-type": "text/event-stream"})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://api.openai.com") as http_client:
        client = OpenAIClient(
            model_name=ModelName.GPT_4O,
            api_key="sk-test-123",
            http_client=http_client,
        )
        assert await client.check_health() is True

        tokens = []
        async for tok in client.astream(messages=[{"role": "user", "content": "Hi"}]):
            tokens.append(tok)

        assert "".join(tokens) == "Shreyas Doshi"


@pytest.mark.asyncio
async def test_openai_client_http_error_handling() -> None:
    """Test OpenAIClient raises ModelProviderException on upstream errors."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="https://api.openai.com") as http_client:
        client = OpenAIClient(
            api_key="sk-test",
            http_client=http_client,
        )
        with pytest.raises(ModelProviderException, match="OpenAI API returned status 429"):
            async for _ in client.astream(messages=[{"role": "user", "content": "Hi"}]):
                pass


# ==========================================
# Ollama Client Tests
# ==========================================
@pytest.mark.asyncio
async def test_ollama_client_streaming_success() -> None:
    """Test OllamaClient parses JSON lines stream from local daemon."""
    json_lines = [
        json.dumps({"message": {"role": "assistant", "content": "Retention "}, "done": False}) + "\n",
        json.dumps({"message": {"role": "assistant", "content": "Curves"}, "done": True}) + "\n",
    ]
    raw_response = "".join(json_lines).encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/api/tags"):
            return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})
        return httpx.Response(200, content=raw_response, headers={"content-type": "application/x-ndjson"})

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport, base_url="http://localhost:11434") as http_client:
        client = OllamaClient(
            model_name=ModelName.LLAMA_3_2,
            http_client=http_client,
        )
        assert await client.check_health() is True

        tokens = []
        async for tok in client.astream(messages=[{"role": "user", "content": "Explain retention"}]):
            tokens.append(tok)

        assert "".join(tokens) == "Retention Curves"


@pytest.mark.asyncio
async def test_ollama_client_unreachable_raises_ollama_unavailable() -> None:
    """Test OllamaClient catches connection errors and raises OllamaUnavailableException with guidance."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused on port 11434", request=request)

    mock_transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=mock_transport, base_url="http://localhost:11434") as http_client:
        client = OllamaClient(
            model_name=ModelName.LLAMA_3_2,
            http_client=http_client,
        )
        assert await client.check_health() is False

        with pytest.raises(OllamaUnavailableException) as exc_info:
            async for _ in client.astream(messages=[{"role": "user", "content": "Hi"}]):
                pass

        assert "Ollama daemon is unreachable" in str(exc_info.value.message)
        assert "ollama serve" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_ollama_client_model_not_found_raises() -> None:
    """Test OllamaClient raises ModelProviderException with pull instructions when model is missing (404)."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(404, json={"error": "model 'nonexistent-model' not found"})
    )
    async with httpx.AsyncClient(transport=mock_transport, base_url="http://localhost:11434") as http_client:
        client = OllamaClient(
            model_name="nonexistent-model",
            http_client=http_client,
        )
        with pytest.raises(ModelProviderException, match="Run `ollama pull nonexistent-model`"):
            async for _ in client.astream(messages=[{"role": "user", "content": "Hi"}]):
                pass
