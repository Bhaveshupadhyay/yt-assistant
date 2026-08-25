"""Base abstract interface for flexible LLM model provider backends."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
import logging
from typing import Any
from app.core.enums import ModelName, ModelProvider

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract base class for all LLM provider clients (Anthropic, OpenAI, Ollama)."""

    def __init__(
        self,
        model_name: str | ModelName,
        provider: ModelProvider,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ) -> None:
        """Initialize the BaseLLMClient.

        Args:
            model_name: Identifier for the underlying model.
            provider: ModelProvider enum representing the provider type.
            default_temperature: Default sampling temperature.
            default_max_tokens: Default max token limit for response generation.
        """
        self.model_name: str = model_name.value if isinstance(model_name, ModelName) else str(model_name)
        self.provider: ModelProvider = provider
        self.default_temperature: float = default_temperature
        self.default_max_tokens: int = default_max_tokens

    @abstractmethod
    async def astream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Asynchronously stream response tokens from the model.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            system_prompt: Optional system prompt to instruct the model.
            temperature: Optional temperature override.
            max_tokens: Optional maximum tokens override.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Incremental text tokens as they are generated.
        """
        yield ""  # pragma: no cover

    async def acomplete(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Asynchronously generate a complete text response by consuming the token stream.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            system_prompt: Optional system prompt.
            temperature: Optional temperature override.
            max_tokens: Optional maximum tokens override.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The complete concatenated response string.
        """
        chunks: list[str] = []
        async for chunk in self.astream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    async def astream_chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Backwards-compatible alias for astream."""
        async for token in self.astream(messages=messages, system_prompt=system_prompt, **kwargs):
            yield token

    @abstractmethod
    async def check_health(self) -> bool:
        """Check whether the model provider backend is reachable and responsive.

        Returns:
            bool: True if healthy, False otherwise.
        """
        pass
