"""Ollama local LLM client implementation with connection health checks and streaming."""

from collections.abc import AsyncGenerator
import json
import logging
from typing import Any
import httpx
from app.core.clients import get_ollama_client
from app.core.config import Settings, get_settings
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import ModelProviderException, OllamaUnavailableException
from app.services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """Local Ollama LLM client (e.g. llama3.2, mistral, qwen2.5) running on http://localhost:11434."""

    def __init__(
        self,
        model_name: str | ModelName = ModelName.LLAMA_3_2,
        base_url: str | None = None,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ) -> None:
        """Initialize OllamaClient.

        Args:
            model_name: Identifier for the local model (e.g. llama3.2, mistral).
            base_url: Base URL for local Ollama daemon (defaults to settings.OLLAMA_BASE_URL).
            settings: Optional application settings.
            http_client: Optional pre-configured httpx.AsyncClient.
            default_temperature: Sampling temperature.
            default_max_tokens: Maximum tokens in response.
        """
        super().__init__(
            model_name=model_name,
            provider=ModelProvider.OLLAMA,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
        )
        self.settings = settings or get_settings()
        self.base_url = base_url or self.settings.OLLAMA_BASE_URL
        self._http_client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        """Return active or cached httpx.AsyncClient."""
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        return get_ollama_client(self.settings)

    async def check_health(self) -> bool:
        """Check whether local Ollama daemon is reachable and responding on port 11434.

        Returns:
            bool: True if daemon responded with 200, False otherwise.
        """
        url = "/api/tags" if self.client.base_url and "localhost" in str(self.client.base_url) else f"{self.base_url.rstrip('/')}/api/tags"
        try:
            resp = await self.client.get(url, timeout=1.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _prepare_payload(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Format messages and runtime options for Ollama Chat API."""
        formatted_messages: list[dict[str, str]] = []

        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        if not formatted_messages:
            formatted_messages.append({"role": "user", "content": "Hello"})

        options: dict[str, Any] = {
            "temperature": temperature if temperature is not None else self.default_temperature,
        }
        if max_tokens or self.default_max_tokens:
            options["num_predict"] = max_tokens or self.default_max_tokens

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": True,
            "options": options,
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
        """Stream tokens from local Ollama daemon.

        Yields:
            str: Incremental generated content.

        Raises:
            OllamaUnavailableException: If Ollama daemon is not running or unreachable.
            ModelProviderException: If Ollama returns a model error (e.g. model not found).
        """
        payload = self._prepare_payload(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        url = "/api/chat" if self.client.base_url and "localhost" in str(self.client.base_url) else f"{self.base_url.rstrip('/')}/api/chat"

        try:
            async with self.client.stream(
                "POST",
                url,
                json=payload,
                timeout=httpx.Timeout(connect=2.0, read=120.0, write=10.0, pool=5.0),
            ) as response:
                if response.status_code == 404:
                    error_body = await response.aread()
                    raise ModelProviderException(
                        f"Ollama model '{self.model_name}' was not found. "
                        f"Run `ollama pull {self.model_name}` to download it, or switch models. Details: {error_body.decode('utf-8', errors='ignore')}"
                    )
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise ModelProviderException(
                        f"Ollama returned HTTP error {response.status_code}: {error_body.decode('utf-8', errors='ignore')}"
                    )

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                        msg_chunk = chunk.get("message", {})
                        content_piece = msg_chunk.get("content", "")
                        if content_piece:
                            yield content_piece

                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError) as exc:
            logger.warning(f"Failed to connect to local Ollama daemon at {self.base_url}: {exc}")
            raise OllamaUnavailableException(
                message=(
                    f"Ollama daemon is unreachable on {self.base_url}. "
                    "Ensure Ollama is running (`ollama serve`) or toggle to a Cloud provider (Claude/OpenAI)."
                ),
                details=str(exc),
            ) from exc
        except httpx.HTTPError as exc:
            if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
                raise OllamaUnavailableException(details=str(exc)) from exc
            logger.error(f"Ollama HTTP communication error: {exc}")
            raise ModelProviderException(f"Ollama communication failure: {exc}") from exc
