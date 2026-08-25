"""Pydantic schemas for Chat endpoints and Server-Sent Events (SSE)."""

from typing import Any
import uuid
from pydantic import BaseModel, Field
from app.schemas.artifact import ArtifactRead
from app.schemas.message import CitationSchema


class ChatRequest(BaseModel):
    """Payload for POST /api/v1/chat endpoint."""

    session_id: uuid.UUID = Field(..., description="Target chat session ID")
    message: str = Field(..., min_length=1, max_length=10000, description="User prompt or question")
    model: str | None = Field(
        default=None,
        description="Optional model identifier override (e.g. 'claude-3-5-sonnet', 'llama3.2', 'gpt-4o')",
    )
    skill: str | None = Field(
        default=None,
        description="Optional skill execution mode ('standard', 'ship30', 'artifact')",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of transcript excerpts to retrieve",
    )


class ChatStatusPayload(BaseModel):
    """Payload for 'status' SSE event."""

    stage: str = Field(..., description="Current processing stage: 'retrieval', 'generation', 'complete'")
    message: str = Field(..., description="Human-readable progress status description")


class ChatTokenPayload(BaseModel):
    """Payload for 'token' SSE event."""

    delta: str = Field(..., description="Incremental generated token text")


class ChatDonePayload(BaseModel):
    """Payload for 'done' SSE event indicating generation stream termination."""

    session_id: uuid.UUID = Field(..., description="Chat session ID")
    message_id: uuid.UUID = Field(..., description="Persisted assistant message ID")
    model_used: str = Field(..., description="Model identifier used for generation")
    citations_count: int = Field(default=0, description="Number of grounded citations")
    has_artifact: bool = Field(default=False, description="Whether an artifact was generated and persisted")
    finish_reason: str = Field(default="stop", description="Stream completion reason")


class ChatErrorPayload(BaseModel):
    """Payload for 'error' SSE event."""

    type: str = Field(..., description="Error exception type")
    message: str = Field(..., description="User-facing error description")
    status_code: int = Field(default=500, description="HTTP status code corresponding to error")
