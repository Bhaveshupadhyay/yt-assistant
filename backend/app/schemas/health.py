"""Pydantic schemas for health & diagnostics using HealthStatus Enum."""

from datetime import datetime
from pydantic import BaseModel, Field
from app.core.enums import HealthStatus


class HealthResponse(BaseModel):
    """System health check response."""

    status: HealthStatus = Field(default=HealthStatus.OK, description="Overall system health status")
    database: bool = Field(..., description="Database connectivity status")
    ollama: bool = Field(..., description="Ollama daemon connectivity status")
    timestamp: datetime = Field(..., description="Timestamp of health check")
    version: str = Field(..., description="Application version")
