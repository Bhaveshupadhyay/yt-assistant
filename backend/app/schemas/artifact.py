"""Pydantic schemas for Artifact domain using ArtifactType Enum."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import ArtifactType


class ArtifactBase(BaseModel):
    """Base fields for an artifact."""

    artifact_type: ArtifactType = Field(
        ...,
        description="Type of generated artifact: html, markdown, or svg",
    )
    title: str = Field(..., max_length=255, description="Artifact title")
    content: str = Field(..., description="Full content (HTML, Markdown, or SVG payload)")


class ArtifactCreate(ArtifactBase):
    """Schema for creating a new artifact."""

    session_id: uuid.UUID = Field(..., description="ID of parent chat session")
    message_id: uuid.UUID | None = Field(default=None, description="Optional ID of associated message")


class ArtifactRead(ArtifactBase):
    """Schema for reading an artifact."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    message_id: uuid.UUID | None
    created_at: datetime
