"""OpenAI LLM client implementation supporting asynchronous streaming."""

from collections.abc import AsyncGenerator
import json
import logging
from typing import Any
import httpx
from app.core.clients import get_openai_client
from app.core.config import Settings, get_settings
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import ModelProviderException
from app.services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI API client (e.g. GPT-4o) with streaming and robust error handling."""

    def __init__(
        self,
        model_name: str | ModelName = ModelName.GPT_4O,
        api_key: str | None = None,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ) -> None:
        """Initialize OpenAIClient.

        Args:
            model_name: OpenAI model identifier.
            api_key: OpenAI API Key (defaults to settings.OPENAI_API_KEY).
            settings: Optional application settings.
            http_client: Optional pre-configured httpx.AsyncClient.
            default_temperature: Sampling temperature.
            default_max_tokens: Max output tokens.
        """
        super().__init__(
            model_name=model_name,
            provider=ModelProvider.OPENAI,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
        )
        self.settings = settings or get_settings()
        self.api_key = api_key or self.settings.OPENAI_API_KEY
        self._http_client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        """Return active or cached httpx.AsyncClient."""
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        return get_openai_client(self.settings)

    def _prepare_payload(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Format messages and system prompt for OpenAI Chat Completions API."""
        formatted_messages: list[dict[str, str]] = []

        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
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
        """Stream tokens from OpenAI Chat Completions API.

        Yields:
            str: Delta text fragments.

        Raises:
            ModelProviderException: When API keys are missing or upstream errors occur.
        """
        if not self.api_key:
            raise ModelProviderException(
                "OpenAI API key is not configured. Set OPENAI_API_KEY or switch to local Ollama."
            )

        payload = self._prepare_payload(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        headers = {
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

        url = "/chat/completions" if self.client.base_url and str(self.client.base_url).startswith("https://api.openai.com") else "https://api.openai.com/v1/chat/completions"

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
                    logger.error(f"OpenAI API error ({response.status_code}): {error_msg}")
                    raise ModelProviderException(
                        f"OpenAI API returned status {response.status_code}: {error_msg}"
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
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content_piece = delta.get("content")
                            if content_piece:
                                yield content_piece
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPError as exc:
            logger.error(f"OpenAI HTTP communication failure: {exc}")
            raise ModelProviderException(f"Failed to communicate with OpenAI: {exc}") from exc

    async def check_health(self) -> bool:
        """Verify that OpenAI API key is set."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)
