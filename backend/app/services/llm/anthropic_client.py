"""Anthropic Claude LLM client implementation supporting asynchronous streaming."""

from collections.abc import AsyncGenerator
import json
import logging
from typing import Any
import httpx
from app.core.clients import get_anthropic_client
from app.core.config import Settings, get_settings
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import ModelProviderException
from app.services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API client with streaming and robust error handling."""

    def __init__(
        self,
        model_name: str | ModelName = ModelName.CLAUDE_3_5_SONNET,
        api_key: str | None = None,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ) -> None:
        """Initialize AnthropicClient.

        Args:
            model_name: Anthropic model identifier.
            api_key: Anthropic API Key (defaults to settings.ANTHROPIC_API_KEY).
            settings: Optional application settings.
            http_client: Optional pre-configured httpx.AsyncClient.
            default_temperature: Sampling temperature (0.0 to 1.0).
            default_max_tokens: Maximum tokens in response.
        """
        super().__init__(
            model_name=model_name,
            provider=ModelProvider.ANTHROPIC,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
        )
        self.settings = settings or get_settings()
        self.api_key = api_key or self.settings.ANTHROPIC_API_KEY
        self._http_client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        """Return active or cached httpx.AsyncClient."""
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        return get_anthropic_client(self.settings)

    def _prepare_payload(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Format messages and system instructions for Anthropic Messages API."""
        formatted_messages: list[dict[str, str]] = []
        extracted_system: list[str] = []

        if system_prompt:
            extracted_system.append(system_prompt)

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                extracted_system.append(content)
            elif role in ("user", "assistant"):
                formatted_messages.append({"role": role, "content": content})

        if not formatted_messages:
            formatted_messages.append({"role": "user", "content": "Hello"})

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted_messages,
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "stream": True,
        }

        if extracted_system:
            payload["system"] = "\n\n".join(extracted_system)

        # Allow extra parameters (e.g. stop_sequences)
        payload.update(kwargs)
        return payload

    async def astream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Anthropic Messages API.

        Yields:
            str: Token fragments as they arrive from Claude.

        Raises:
            ModelProviderException: When API keys are missing or upstream errors occur.
        """
        if not self.api_key:
            raise ModelProviderException(
                "Anthropic API key is not configured. Set ANTHROPIC_API_KEY or switch to local Ollama."
            )

        payload = self._prepare_payload(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        url = "/messages" if self.client.base_url and str(self.client.base_url).startswith("https://api.anthropic.com") else "https://api.anthropic.com/v1/messages"

        try:
            async with self.client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=5.0),
            ) as response:
                if response.status_code != 200:
                    error_bytes = await response.aread()
                    error_msg = error_bytes.decode("utf-8", errors="replace")
                    logger.error(f"Anthropic API error ({response.status_code}): {error_msg}")
                    raise ModelProviderException(
                        f"Anthropic API returned status {response.status_code}: {error_msg}"
                    )

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type")

                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                        elif event_type == "error":
                            err_info = data.get("error", {}).get("message", "Unknown Anthropic error")
                            raise ModelProviderException(f"Anthropic stream error: {err_info}")
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPError as exc:
            logger.error(f"Anthropic HTTP communication failure: {exc}")
            raise ModelProviderException(f"Failed to communicate with Anthropic: {exc}") from exc

    async def check_health(self) -> bool:
        """Verify that Anthropic API key is set."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)
