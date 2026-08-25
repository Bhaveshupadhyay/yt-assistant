"""Factory and resolution router for instantiating flexible LLM clients."""

import logging
from typing import Any
import httpx
from app.core.config import Settings, get_settings
from app.core.enums import ModelName, ModelProvider
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.base import BaseLLMClient
from app.services.llm.ollama_client import OllamaClient
from app.services.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


def resolve_provider_for_model(model_name: str | ModelName) -> ModelProvider:
    """Determine the provider (Anthropic, OpenAI, Ollama) from the model name identifier.

    Args:
        model_name: Model identifier string or ModelName enum.

    Returns:
        ModelProvider enum.
    """
    model_str = model_name.value if isinstance(model_name, ModelName) else str(model_name).lower().strip()

    if model_str.startswith("claude"):
        return ModelProvider.ANTHROPIC
    if model_str.startswith("gpt") or model_str.startswith("o1") or model_str.startswith("o3"):
        return ModelProvider.OPENAI
    if (
        model_str.startswith("llama")
        or model_str.startswith("mistral")
        or model_str.startswith("qwen")
        or model_str.startswith("deepseek")
        or model_str.startswith("phi")
        or model_str.startswith("gemma")
    ):
        return ModelProvider.OLLAMA

    # Default to Ollama for local custom models unless recognized
    return ModelProvider.OLLAMA


def get_llm_client(
    model_name: str | ModelName | None = None,
    provider: ModelProvider | str | None = None,
    settings: Settings | None = None,
    http_client: httpx.AsyncClient | None = None,
    **kwargs: Any,
) -> BaseLLMClient:
    """Instantiate and return the appropriate LLM client based on model name or provider.

    Args:
        model_name: Identifier for the model (e.g. 'claude-3-5-sonnet', 'llama3.2', 'gpt-4o').
        provider: Explicit provider override.
        settings: Application settings instance.
        http_client: Optional custom HTTP client.
        **kwargs: Additional kwargs passed to the client constructor.

    Returns:
        BaseLLMClient instance.
    """
    cfg = settings or get_settings()

    # Determine default model if not provided
    if not model_name:
        if cfg.ANTHROPIC_API_KEY:
            model_name = ModelName.CLAUDE_3_5_SONNET
        elif cfg.OPENAI_API_KEY:
            model_name = ModelName.GPT_4O
        else:
            model_name = cfg.OLLAMA_MODEL or ModelName.LLAMA_3_2

    # Determine provider
    if provider:
        if isinstance(provider, str):
            try:
                target_provider = ModelProvider(provider.lower())
            except ValueError:
                target_provider = resolve_provider_for_model(model_name)
        else:
            target_provider = provider
    else:
        target_provider = resolve_provider_for_model(model_name)

    if target_provider == ModelProvider.ANTHROPIC:
        return AnthropicClient(
            model_name=model_name,
            settings=cfg,
            http_client=http_client,
            **kwargs,
        )
    elif target_provider == ModelProvider.OPENAI:
        return OpenAIClient(
            model_name=model_name,
            settings=cfg,
            http_client=http_client,
            **kwargs,
        )
    elif target_provider == ModelProvider.OLLAMA:
        return OllamaClient(
            model_name=model_name,
            settings=cfg,
            http_client=http_client,
            **kwargs,
        )

    # Fallback to Ollama
    return OllamaClient(
        model_name=model_name,
        settings=cfg,
        http_client=http_client,
        **kwargs,
    )
