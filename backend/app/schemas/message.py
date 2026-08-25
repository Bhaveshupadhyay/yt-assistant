"""Pydantic schemas for Message domain using MessageRole Enum."""

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import MessageRole


class CitationSchema(BaseModel):
    """Pydantic schema for verified transcript citations."""

    model_config = ConfigDict(extra="ignore")

    episode_title: str = Field(..., description="Title of the Lenny Podcast episode")
    guest_name: str = Field(..., description="Name of the interview guest")
    guest_role: str | None = Field(default=None, description="Guest company / role")
    timestamp: str | None = Field(default=None, description="Timestamp mark in format MM:SS or HH:MM:SS")
    youtube_url: str | None = Field(default=None, description="YouTube source URL with timestamp")
    snippet: str | None = Field(default=None, description="Excerpt quote from transcript")


class MessageBase(BaseModel):
    """Base fields for a message."""

    role: MessageRole = Field(..., description="Message author role: user, assistant, or system")
    content: str = Field(..., description="Text content of the message")
    citations: list[CitationSchema] = Field(
        default_factory=list,
        description="Structured citations referencing Lenny transcripts",
    )
    has_artifact: bool = Field(
        default=False,
        description="Indicates whether this message generated an artifact",
    )


class MessageCreate(MessageBase):
    """Schema for creating a new message."""

    session_id: uuid.UUID = Field(..., description="ID of the parent chat session")


class MessageRead(MessageBase):
    """Schema for reading a message."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime
