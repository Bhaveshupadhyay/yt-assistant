"""Streaming Chat router with Server-Sent Events (SSE), RAG retrieval, citations, and artifact isolation."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.core.dependencies import get_chat_service
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    summary="Stream conversational assistant response with real-time SSE",
    response_description="Server-Sent Events stream: status, token, citations, artifact, done",
)
async def stream_chat(
    payload: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Handle chat interaction with Server-Sent Events (SSE) streaming.

    Streams:
      1. Retrieval status event ('Searching Lenny transcripts...').
      2. Token-by-token LLM stream.
      3. Citation payload event ([{"guest_name": "Elena Verna", ...}]).
      4. Artifact payload event (if generated).
      5. Final completion event with persisted message ID.
    """
    # Preflight check runs before opening StreamingResponse (raises HTTP 503 / 404 if invalid)
    await chat_service.validate_preflight(payload)

    return StreamingResponse(
        chat_service.stream_chat_events(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
