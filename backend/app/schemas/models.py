"""Pydantic schemas for LLM models and provider toggle metadata."""

from pydantic import BaseModel, Field
from app.core.enums import ModelProvider


class ModelItem(BaseModel):
    """Schema representing an individual LLM available for toggling."""

    id: str = Field(..., description="Unique model identifier, e.g. claude-3-5-sonnet, llama3.2")
    name: str = Field(..., description="Human-readable model display name")
    provider: ModelProvider = Field(..., description="Model provider (anthropic, openai, ollama)")
    is_cloud: bool = Field(..., description="True if hosted cloud model, False if local on-device")
    is_available: bool = Field(..., description="Whether provider is currently configured or reachable")
    description: str = Field(..., description="Description of model capabilities and speed")


class ProviderStatus(BaseModel):
    """Schema detailing connectivity and configuration status for a model provider."""

    name: str = Field(..., description="Provider display name")
    configured: bool = Field(..., description="Whether API key or daemon URL is configured")
    connected: bool | None = Field(default=None, description="Liveness check result if applicable")
    endpoint: str | None = Field(default=None, description="Provider endpoint URL if local/custom")


class ModelsResponse(BaseModel):
    """Response schema for GET /api/v1/models."""

    active_model: str = Field(..., description="Current system default active model identifier")
    active_provider: ModelProvider = Field(..., description="Provider corresponding to active model")
    available_models: list[ModelItem] = Field(..., description="List of supported and detected models")
    providers: dict[str, ProviderStatus] = Field(..., description="Status breakdown of provider backends")
