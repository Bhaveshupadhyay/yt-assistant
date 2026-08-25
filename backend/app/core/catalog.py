"""Central Model Catalog and Registry for supported LLM models and providers."""

from dataclasses import dataclass
from app.core.enums import ModelName, ModelProvider


@dataclass(frozen=True)
class ModelSpec:
    """Immutable model specification containing metadata, provider, and tier descriptions."""

    id: str
    name: str
    provider: ModelProvider
    is_cloud: bool
    description: str


class ModelRegistry:
    """Central single source of truth for all supported model specifications."""

    _CATALOG: list[ModelSpec] = [
        ModelSpec(
            id=ModelName.CLAUDE_3_5_SONNET.value,
            name="Claude 3.5 Sonnet",
            provider=ModelProvider.ANTHROPIC,
            is_cloud=True,
            description="High-fidelity strategic thinking, nuanced reasoning, and fast response generation (Cloud).",
        ),
        ModelSpec(
            id=ModelName.CLAUDE_3_7_SONNET.value,
            name="Claude 3.7 Sonnet",
            provider=ModelProvider.ANTHROPIC,
            is_cloud=True,
            description="State-of-the-art hybrid reasoning, coding, and synthesis model (Cloud).",
        ),
        ModelSpec(
            id=ModelName.GEMINI_3_6_FLASH.value,
            name="Gemini 3.6 Flash",
            provider=ModelProvider.GEMINI,
            is_cloud=True,
            description="Next-gen high-speed multimodal reasoning with massive context window (Cloud).",
        ),
        ModelSpec(
            id=ModelName.GEMINI_3_6_FLASH_LITE.value,
            name="Gemini 3.6 Flash Lite",
            provider=ModelProvider.GEMINI,
            is_cloud=True,
            description="Ultra-lightweight, low-latency Google model optimized for high-throughput tasks (Cloud).",
        ),
        ModelSpec(
            id=ModelName.GEMINI_3_7_PRO.value,
            name="Gemini 3.7 Pro",
            provider=ModelProvider.GEMINI,
            is_cloud=True,
            description="Google flagship intelligence with frontier reasoning, coding, and synthesis (Cloud).",
        ),
        ModelSpec(
            id=ModelName.GPT_4O.value,
            name="GPT-4o",
            provider=ModelProvider.OPENAI,
            is_cloud=True,
            description="Flagship multimodal intelligence with strong structured output generation (Cloud).",
        ),
        ModelSpec(
            id=ModelName.GPT_4O_MINI.value,
            name="GPT-4o Mini",
            provider=ModelProvider.OPENAI,
            is_cloud=True,
            description="Ultra-fast, cost-efficient model for quick responses (Cloud).",
        ),
        ModelSpec(
            id=ModelName.LLAMA_3_2_1B.value,
            name="Llama 3.2 (1B Ultra-Fast)",
            provider=ModelProvider.OLLAMA,
            is_cloud=False,
            description="Ultra-lightweight on-device model optimized for low memory footprint and high speed locally.",
        ),
        ModelSpec(
            id=ModelName.LLAMA_3_2.value,
            name="Llama 3.2 (3B)",
            provider=ModelProvider.OLLAMA,
            is_cloud=False,
            description="Optimized on-device edge model running locally via Ollama with zero data egress.",
        ),
        ModelSpec(
            id=ModelName.MISTRAL.value,
            name="Mistral (7B)",
            provider=ModelProvider.OLLAMA,
            is_cloud=False,
            description="Fast and capable open-weights instruction model for local deployment.",
        ),
        ModelSpec(
            id=ModelName.QWEN_2_5.value,
            name="Qwen 2.5",
            provider=ModelProvider.OLLAMA,
            is_cloud=False,
            description="Multilingual reasoning and code-specialized model running locally via Ollama.",
        ),
        ModelSpec(
            id=ModelName.DEEPSEEK_R1.value,
            name="DeepSeek R1",
            provider=ModelProvider.OLLAMA,
            is_cloud=False,
            description="Open reasoning & chain-of-thought distillation model running locally via Ollama.",
        ),
    ]

    @classmethod
    def get_all(cls) -> list[ModelSpec]:
        """Return the complete list of supported model specifications."""
        return list(cls._CATALOG)

    @classmethod
    def get(cls, model_id: str) -> ModelSpec | None:
        """Lookup a model specification by its unique identifier."""
        return next((m for m in cls._CATALOG if m.id == model_id), None)

    @classmethod
    def get_by_provider(cls, provider: ModelProvider) -> list[ModelSpec]:
        """Retrieve all models associated with a specific provider."""
        return [m for m in cls._CATALOG if m.provider == provider]

    @classmethod
    def is_supported(cls, model_id: str) -> bool:
        """Check whether a model identifier is registered in the catalog."""
        return any(m.id == model_id for m in cls._CATALOG)
