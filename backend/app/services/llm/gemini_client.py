"""Google Gemini LLM client implementation supporting asynchronous streaming."""

from collections.abc import AsyncGenerator
import json
import logging
from typing import Any
import httpx
from app.core.clients import get_gemini_client
from app.core.config import Settings, get_settings
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import ModelProviderException
from app.services.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Google Gemini API client with streaming and decoupled HTTPX architecture."""

    def __init__(
        self,
        model_name: str | ModelName = ModelName.GEMINI_2_0_FLASH,
        api_key: str | None = None,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ) -> None:
        """Initialize GeminiClient.

        Args:
            model_name: Gemini model identifier (e.g. 'gemini-2.0-flash', 'gemini-1.5-pro').
            api_key: Gemini API Key (defaults to settings.GEMINI_API_KEY).
            settings: Optional application settings.
            http_client: Optional pre-configured httpx.AsyncClient.
            default_temperature: Sampling temperature (0.0 to 2.0).
            default_max_tokens: Maximum tokens in response.
        """
        super().__init__(
            model_name=model_name,
            provider=ModelProvider.GEMINI,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
        )
        self.settings = settings or get_settings()
        self.api_key = api_key or self.settings.GEMINI_API_KEY
        self._http_client = http_client

    @property
    def client(self) -> httpx.AsyncClient:
        """Return active or cached httpx.AsyncClient."""
        if self._http_client is not None and not self._http_client.is_closed:
            return self._http_client
        return get_gemini_client(self.settings)

    def _prepare_payload(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Format messages and system instructions for Google Gemini GenerateContent API."""
        contents: list[dict[str, Any]] = []
        system_parts: list[str] = []

        if system_prompt:
            system_parts.append(system_prompt)

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}],
                })

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.default_temperature,
                "maxOutputTokens": max_tokens or self.default_max_tokens,
            },
        }

        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}],
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
        """Stream tokens from Google Gemini REST SSE API.

        Yields:
            str: Token fragments as they arrive from Gemini.

        Raises:
            ModelProviderException: When API keys are missing or upstream errors occur.
        """
        if not self.api_key:
            raise ModelProviderException(
                "Gemini API key is not configured. Set GEMINI_API_KEY in environment or toggle to local Ollama/Cloud."
            )

        payload = self._prepare_payload(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        headers = {
            "x-goog-api-key": self.api_key,
            "content-type": "application/json",
        }

        url = f"/models/{self.model_name}:streamGenerateContent?alt=sse"

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
                    logger.error(f"Gemini API error ({response.status_code}): {error_msg}")
                    raise ModelProviderException(
                        f"Gemini API returned status {response.status_code}: {error_msg}"
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
                        if "error" in data:
                            err_info = data.get("error", {}).get("message", "Unknown Gemini error")
                            raise ModelProviderException(f"Gemini stream error: {err_info}")

                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text_chunk = part.get("text", "")
                                if text_chunk:
                                    yield text_chunk
                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPError as exc:
            logger.error(f"Gemini HTTP communication failure: {exc}")
            raise ModelProviderException(f"Failed to communicate with Gemini: {exc}") from exc

    async def check_health(self) -> bool:
        """Verify that Gemini API key is configured."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)
