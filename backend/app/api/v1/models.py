"""Models router for listing active model, catalog, and verified operational models."""

import logging
import time
from fastapi import APIRouter, Depends, status
from app.core.clients import get_gemini_client, get_ollama_client
from app.core.config import Settings, get_settings
from app.core.enums import ModelName, ModelProvider
from app.schemas.models import (
    AvailableWorkingModelsResponse,
    ModelItem,
    ModelsResponse,
    ProviderHealthSummary,
    ProviderStatus,
    WorkingModelItem,
)
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
        "id": ModelName.GEMINI_3_6_FLASH.value,
        "name": "Gemini 3.6 Flash",
        "provider": ModelProvider.GEMINI,
        "is_cloud": True,
        "description": "Next-gen high-speed multimodal reasoning with massive context window (Cloud).",
    },
    {
        "id": ModelName.GEMINI_3_6_FLASH_LITE.value,
        "name": "Gemini 3.6 Flash Lite",
        "provider": ModelProvider.GEMINI,
        "is_cloud": True,
        "description": "Ultra-lightweight, low-latency Google model optimized for high-throughput tasks (Cloud).",
    },
    {
        "id": ModelName.GEMINI_3_7_PRO.value,
        "name": "Gemini 3.7 Pro",
        "provider": ModelProvider.GEMINI,
        "is_cloud": True,
        "description": "Google flagship intelligence with frontier reasoning, coding, and synthesis (Cloud).",
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
    gemini_configured = bool(settings.GEMINI_API_KEY)

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
    elif gemini_configured:
        active_model = ModelName.GEMINI_3_6_FLASH.value
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
        elif provider == ModelProvider.GEMINI:
            is_available = gemini_configured
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
            connected=None,
        ),
        ModelProvider.GEMINI.value: ProviderStatus(
            name="Google Gemini",
            configured=gemini_configured,
            connected=None,
        ),
        ModelProvider.OPENAI.value: ProviderStatus(
            name="OpenAI",
            configured=openai_configured,
            connected=None,
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


@router.get(
    "/available",
    response_model=AvailableWorkingModelsResponse,
    status_code=status.HTTP_200_OK,
    summary="List all verified operational and working models",
)
@router.get(
    "/working",
    response_model=AvailableWorkingModelsResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_available_working_models(
    settings: Settings = Depends(get_settings),
) -> AvailableWorkingModelsResponse:
    """Actively verify live connectivity and return all currently working models across providers."""
    working_models: list[WorkingModelItem] = []
    providers_summary: dict[str, ProviderHealthSummary] = {}

    # 1. Check Anthropic
    anthropic_configured = bool(settings.ANTHROPIC_API_KEY and len(settings.ANTHROPIC_API_KEY.strip()) > 0)
    if anthropic_configured:
        anthropic_models = [m for m in SUPPORTED_MODELS_CATALOG if m["provider"] == ModelProvider.ANTHROPIC]
        for m in anthropic_models:
            working_models.append(
                WorkingModelItem(
                    id=m["id"],
                    name=m["name"],
                    provider=m["provider"],
                    is_cloud=True,
                    status="operational",
                    description=m["description"],
                )
            )
        providers_summary[ModelProvider.ANTHROPIC.value] = ProviderHealthSummary(
            name="Anthropic Claude",
            status="operational",
            configured=True,
            models_count=len(anthropic_models),
            message="API credentials configured; live probe not performed.",
        )
    else:
        providers_summary[ModelProvider.ANTHROPIC.value] = ProviderHealthSummary(
            name="Anthropic Claude",
            status="unconfigured",
            configured=False,
            models_count=0,
            message="ANTHROPIC_API_KEY is not configured.",
        )

    # 2. Check Google Gemini
    gemini_configured = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 0)
    if gemini_configured:
        gemini_models = [m for m in SUPPORTED_MODELS_CATALOG if m["provider"] == ModelProvider.GEMINI]
        gemini_latency: float | None = None
        gemini_status = "operational"
        gemini_msg = "Google Gemini API operational."

        try:
            gemini_client = get_gemini_client(settings)
            start_t = time.perf_counter()
            resp = await gemini_client.get(
                "/models",
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                timeout=2.0,
            )
            gemini_latency = round((time.perf_counter() - start_t) * 1000, 2)
            if resp.status_code == 200:
                gemini_status = "operational"
            elif resp.status_code in (400, 403):
                gemini_status = "unauthorized"
                gemini_msg = f"Gemini API returned status {resp.status_code}: invalid API key."
            else:
                gemini_status = "degraded"
                gemini_msg = f"Gemini API returned status {resp.status_code}."
        except Exception as exc:
            logger.debug(f"Gemini live health check failed: {exc}")
            gemini_status = "unreachable"
            gemini_msg = f"Gemini API is unreachable: {exc}"

        if gemini_status in ("operational", "degraded"):
            for m in gemini_models:
                working_models.append(
                    WorkingModelItem(
                        id=m["id"],
                        name=m["name"],
                        provider=m["provider"],
                        is_cloud=True,
                        status=gemini_status,
                        latency_ms=gemini_latency,
                        description=m["description"],
                    )
                )

        providers_summary[ModelProvider.GEMINI.value] = ProviderHealthSummary(
            name="Google Gemini",
            status=gemini_status,
            configured=True,
            models_count=len(gemini_models) if gemini_status in ("operational", "degraded") else 0,
            message=gemini_msg,
        )
    else:
        providers_summary[ModelProvider.GEMINI.value] = ProviderHealthSummary(
            name="Google Gemini",
            status="unconfigured",
            configured=False,
            models_count=0,
            message="GEMINI_API_KEY is not configured.",
        )

    # 3. Check OpenAI
    openai_configured = bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 0)
    if openai_configured:
        openai_models = [m for m in SUPPORTED_MODELS_CATALOG if m["provider"] == ModelProvider.OPENAI]
        for m in openai_models:
            working_models.append(
                WorkingModelItem(
                    id=m["id"],
                    name=m["name"],
                    provider=m["provider"],
                    is_cloud=True,
                    status="operational",
                    description=m["description"],
                )
            )
        providers_summary[ModelProvider.OPENAI.value] = ProviderHealthSummary(
            name="OpenAI",
            status="operational",
            configured=True,
            models_count=len(openai_models),
            message="API credentials configured; live probe not performed.",
        )
    else:
        providers_summary[ModelProvider.OPENAI.value] = ProviderHealthSummary(
            name="OpenAI",
            status="unconfigured",
            configured=False,
            models_count=0,
            message="OPENAI_API_KEY is not configured.",
        )

    # 4. Check Ollama Local Daemon
    ollama_models = [m for m in SUPPORTED_MODELS_CATALOG if m["provider"] == ModelProvider.OLLAMA]
    ollama_connected = False
    ollama_latency: float | None = None
    ollama_msg = "Ollama daemon is running."

    try:
        ollama_client = get_ollama_client(settings)
        start_t = time.perf_counter()
        resp = await ollama_client.get("/api/tags", timeout=1.0)
        ollama_latency = round((time.perf_counter() - start_t) * 1000, 2)
        if resp.status_code == 200:
            ollama_connected = True
            for m in ollama_models:
                working_models.append(
                    WorkingModelItem(
                        id=m["id"],
                        name=m["name"],
                        provider=m["provider"],
                        is_cloud=False,
                        status="operational",
                        latency_ms=ollama_latency,
                        description=m["description"],
                    )
                )
        else:
            ollama_msg = f"Ollama daemon returned status {resp.status_code}."
    except Exception as exc:
        logger.debug(f"Ollama live connectivity check failed: {exc}")
        ollama_msg = f"Ollama daemon unreachable on {settings.OLLAMA_BASE_URL}. Run `ollama serve` to activate local models."

    providers_summary[ModelProvider.OLLAMA.value] = ProviderHealthSummary(
        name="Ollama (Local)",
        status="operational" if ollama_connected else "unreachable",
        configured=bool(settings.OLLAMA_BASE_URL),
        models_count=len(ollama_models) if ollama_connected else 0,
        message=ollama_msg,
    )

    return AvailableWorkingModelsResponse(
        total_working=len(working_models),
        working_models=working_models,
        providers=providers_summary,
    )
