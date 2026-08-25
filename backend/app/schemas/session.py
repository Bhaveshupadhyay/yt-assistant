"""Pydantic schemas for ChatSession domain using Enums."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import ModelName
from app.schemas.artifact import ArtifactRead
from app.schemas.message import MessageRead


class SessionBase(BaseModel):
    """Base fields for a session."""

    title: str = Field(
        default="New Conversation",
        max_length=255,
        description="User-visible session title",
    )
    model_used: str = Field(
        default=ModelName.CLAUDE_3_5_SONNET.value,
        max_length=100,
        description="Active model identifier (e.g. claude-3-5-sonnet, llama3.2)",
    )


class SessionCreate(BaseModel):
    """Schema for requesting a new session."""

    title: str = Field(
        default="New Conversation",
        max_length=255,
        description="Optional title for the conversation",
    )
    model_used: str = Field(
        default=ModelName.CLAUDE_3_5_SONNET.value,
        max_length=100,
        description="Model to use for this session",
    )


class SessionUpdate(BaseModel):
    """Schema for updating an existing session."""

    title: str | None = Field(default=None, max_length=255)
    model_used: str | None = Field(default=None, max_length=100)


class SessionRead(SessionBase):
    """Schema for reading a session summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionRead):
    """Schema for reading a full session including message history and artifacts."""

    messages: list[MessageRead] = Field(default_factory=list)
    artifacts: list[ArtifactRead] = Field(default_factory=list)
