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


class WorkingModelItem(BaseModel):
    """Schema representing an actively verified, operational model."""

    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    provider: ModelProvider = Field(..., description="Model provider")
    is_cloud: bool = Field(..., description="Whether hosted cloud or local")
    status: str = Field(default="operational", description="Operational status: operational, degraded, or offline")
    latency_ms: float | None = Field(default=None, description="Health-check response latency in milliseconds")
    description: str | None = Field(default=None, description="Model description")


class ProviderHealthSummary(BaseModel):
    """Provider health summary detailing connectivity and model counts."""

    name: str = Field(..., description="Provider display name")
    status: str = Field(..., description="Status: operational, unconfigured, or unreachable")
    configured: bool = Field(..., description="Whether credentials or endpoints are set")
    models_count: int = Field(..., description="Number of active working models for this provider")
    message: str | None = Field(default=None, description="Detailed status or diagnostic message")


class AvailableWorkingModelsResponse(BaseModel):
    """Response schema for GET /api/v1/models/available."""

    total_working: int = Field(..., description="Total count of verified working models")
    working_models: list[WorkingModelItem] = Field(..., description="List of verified working models")
    providers: dict[str, ProviderHealthSummary] = Field(..., description="Provider health summaries")
