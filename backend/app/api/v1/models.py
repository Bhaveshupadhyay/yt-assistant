"""Models router for listing active model and available providers."""

import logging
from fastapi import APIRouter, Depends, status
from app.core.clients import get_ollama_client
from app.core.config import Settings, get_settings
from app.core.enums import ModelName, ModelProvider
from app.schemas.models import ModelItem, ModelsResponse, ProviderStatus
from app.services.llm.factory import resolve_provider_for_model

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["Models"])

# Supported catalog of standard models
SUPPORTED_MODELS_CATALOG = [
    {
        "id": ModelName.CLAUDE_3_5_SONNET.value,
        "name": "Claude 3.5 Sonnet",
        "provider": ModelProvider.ANTHROPIC,
        "is_cloud": True,
        "description": "High-fidelity strategic thinking, nuanced reasoning, and fast response generation (Cloud).",
    },
    {
        "id": ModelName.CLAUDE_3_7_SONNET.value,
        "name": "Claude 3.7 Sonnet",
        "provider": ModelProvider.ANTHROPIC,
        "is_cloud": True,
        "description": "State-of-the-art hybrid reasoning, coding, and synthesis model (Cloud).",
    },
    {
        "id": ModelName.GPT_4O.value,
        "name": "GPT-4o",
        "provider": ModelProvider.OPENAI,
        "is_cloud": True,
        "description": "Flagship multimodal intelligence with strong structured output generation (Cloud).",
    },
    {
        "id": ModelName.GPT_4O_MINI.value,
        "name": "GPT-4o Mini",
        "provider": ModelProvider.OPENAI,
        "is_cloud": True,
        "description": "Ultra-fast, cost-efficient model for quick responses (Cloud).",
    },
    {
        "id": ModelName.LLAMA_3_2.value,
        "name": "Llama 3.2 (3B/8B)",
        "provider": ModelProvider.OLLAMA,
        "is_cloud": False,
        "description": "Optimized on-device edge model running locally via Ollama with zero data egress.",
    },
    {
        "id": ModelName.MISTRAL.value,
        "name": "Mistral (7B)",
        "provider": ModelProvider.OLLAMA,
        "is_cloud": False,
        "description": "Fast and capable open-weights instruction model for local deployment.",
    },
    {
        "id": ModelName.QWEN_2_5.value,
        "name": "Qwen 2.5",
        "provider": ModelProvider.OLLAMA,
        "is_cloud": False,
        "description": "Multilingual reasoning and code-specialized model running locally via Ollama.",
    },
    {
        "id": ModelName.DEEPSEEK_R1.value,
        "name": "DeepSeek R1",
        "provider": ModelProvider.OLLAMA,
        "is_cloud": False,
        "description": "Open reasoning & chain-of-thought distillation model running locally via Ollama.",
    },
]


@router.get(
    "",
    response_model=ModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="List active model and toggleable model catalog",
)
async def list_models(
    settings: Settings = Depends(get_settings),
) -> ModelsResponse:
    """Retrieve the currently active model, supported model list, and provider connectivity."""
    anthropic_configured = bool(settings.ANTHROPIC_API_KEY)
    openai_configured = bool(settings.OPENAI_API_KEY)

    # Check Ollama connectivity
    ollama_connected = False
    try:
        ollama_client = get_ollama_client(settings)
        resp = await ollama_client.get("/api/tags", timeout=1.0)
        ollama_connected = resp.status_code == 200
    except Exception as exc:
        logger.debug(f"Ollama daemon check in /models failed: {exc}")

    # Determine default active model
    if anthropic_configured:
        active_model = ModelName.CLAUDE_3_5_SONNET.value
    elif openai_configured:
        active_model = ModelName.GPT_4O.value
    else:
        active_model = settings.OLLAMA_MODEL or ModelName.LLAMA_3_2.value

    active_provider = resolve_provider_for_model(active_model)

    # Build model item list with availability flags
    models_list: list[ModelItem] = []
    for item in SUPPORTED_MODELS_CATALOG:
        provider = item["provider"]
        if provider == ModelProvider.ANTHROPIC:
            is_available = anthropic_configured
        elif provider == ModelProvider.OPENAI:
            is_available = openai_configured
        elif provider == ModelProvider.OLLAMA:
            is_available = ollama_connected
        else:
            is_available = False

        models_list.append(
            ModelItem(
                id=item["id"],
                name=item["name"],
                provider=provider,
                is_cloud=item["is_cloud"],
                is_available=is_available,
                description=item["description"],
            )
        )

    providers_status = {
        ModelProvider.ANTHROPIC.value: ProviderStatus(
            name="Anthropic Claude",
            configured=anthropic_configured,
            connected=anthropic_configured,
        ),
        ModelProvider.OPENAI.value: ProviderStatus(
            name="OpenAI",
            configured=openai_configured,
            connected=openai_configured,
        ),
        ModelProvider.OLLAMA.value: ProviderStatus(
            name="Ollama (Local)",
            configured=bool(settings.OLLAMA_BASE_URL),
            connected=ollama_connected,
            endpoint=settings.OLLAMA_BASE_URL,
        ),
    }

    return ModelsResponse(
        active_model=active_model,
        active_provider=active_provider,
        available_models=models_list,
        providers=providers_status,
    )
