"""Streaming Chat router with Server-Sent Events (SSE), RAG retrieval, citations, and artifact isolation."""

from collections.abc import AsyncGenerator
import json
import logging
import time
from typing import Any
import uuid
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings, get_settings
from app.core.dependencies import (
    get_artifact_repository,
    get_artifact_service,
    get_db,
    get_message_repository,
    get_rag_service,
    get_session_repository,
    get_ship30_service,
)
from app.core.enums import MessageRole
from app.core.exceptions import (
    AppException,
    OllamaUnavailableException,
    SessionNotFoundException,
)
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.chat import (
    ChatDonePayload,
    ChatErrorPayload,
    ChatRequest,
    ChatStatusPayload,
    ChatTokenPayload,
)
from app.services.artifact_service import ArtifactService, ArtifactStreamParser
from app.services.llm.factory import get_llm_client, resolve_provider_for_model
from app.services.rag_service import RAGService
from app.services.ship30_service import Ship30Service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def format_sse(event: str, data: Any) -> str:
    """Format an event name and arbitrary data into standard Server-Sent Event text."""
    if hasattr(data, "model_dump"):
        payload = json.dumps(data.model_dump(), default=str)
    elif isinstance(data, (dict, list)):
        payload = json.dumps(data, default=str)
    else:
        payload = str(data)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post(
    "",
    summary="Stream conversational assistant response with real-time SSE",
    response_description="Server-Sent Events stream: status, token, citations, artifact, done",
)
async def stream_chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    session_repo: SessionRepository = Depends(get_session_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    artifact_repo: ArtifactRepository = Depends(get_artifact_repository),
    rag_service: RAGService = Depends(get_rag_service),
    ship30_service: Ship30Service = Depends(get_ship30_service),
    artifact_service: ArtifactService = Depends(get_artifact_service),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Handle chat interaction with Server-Sent Events (SSE) streaming.

    Streams:
      1. Retrieval status event ('Searching Lenny transcripts...').
      2. Token-by-token LLM stream.
      3. Citation payload event ([{"guest_name": "Elena Verna", ...}]).
      4. Artifact payload event (if generated).
      5. Final completion event with persisted message ID.
    """
    # 1. Validate session existence before opening the SSE stream
    session = await session_repo.get_by_id(payload.session_id)
    if not session:
        raise SessionNotFoundException(session_id=payload.session_id)

    # 2. Persist user prompt in database
    await message_repo.create(
        session_id=payload.session_id,
        role=MessageRole.USER,
        content=payload.message,
    )
    await db.commit()

    # 3. Determine target model and provider
    target_model = payload.model or session.model_used or settings.OLLAMA_MODEL
    provider = resolve_provider_for_model(target_model)

    # If model was explicitly passed, update session model_used
    if payload.model and payload.model != session.model_used:
        await session_repo.update(session_id=payload.session_id, model_used=payload.model)
        await db.commit()

    async def sse_event_generator() -> AsyncGenerator[str, None]:
        start_time = time.perf_counter()
        token_count = 0
        chunks: list[dict[str, Any]] = []
        citations_data: list[dict[str, Any]] = []
        full_generated_tokens: list[str] = []

        try:
            # ─── Stage 1: Retrieval Status ────────────────────────────────────
            yield format_sse(
                "status",
                ChatStatusPayload(stage="retrieval", message="Searching Lenny transcripts..."),
            )

            # Perform hybrid dense + sparse retrieval
            chunks = await rag_service.retrieve(query=payload.message, top_k=payload.top_k)
            citations = rag_service.extract_citations(chunks)
            citations_data = [c.model_dump() for c in citations]
            is_fallback = rag_service.is_fallback_needed(chunks)

            # ─── Stage 2: Prompt Assembly & Generation Status ─────────────────
            yield format_sse(
                "status",
                ChatStatusPayload(stage="generation", message="Synthesizing answer from transcripts..."),
            )

            # Check if specialized skill requested
            is_ship30 = payload.skill == "ship30" or (
                not payload.skill and "ship 30" in payload.message.lower()
            )

            # Instantiate LLM client
            llm_client = get_llm_client(model_name=target_model, settings=settings)

            # Zero-hallucination fallback check
            if is_fallback and not is_ship30:
                fallback_msg = rag_service.get_zero_hallucination_fallback()
                for word in fallback_msg.split(" "):
                    delta = word + " "
                    token_count += 1
                    full_generated_tokens.append(delta)
                    yield format_sse("token", ChatTokenPayload(delta=delta))
                clean_text = fallback_msg.strip()
                extracted_artifacts = []
            else:
                # Fetch conversation history for session context
                prior_messages = await message_repo.get_by_session_id(payload.session_id, limit=20)
                history_list = [
                    {"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content}
                    for m in prior_messages[:-1]  # Exclude current prompt already inserted
                ]

                if is_ship30:
                    system_prompt = ship30_service.build_ship30_system_prompt()
                    user_prompt = ship30_service.build_ship30_user_prompt(
                        topic=payload.message, context_chunks=chunks
                    )
                    messages = [{"role": "user", "content": user_prompt}]
                else:
                    system_prompt, messages = rag_service.build_grounded_messages(
                        query=payload.message,
                        retrieved_chunks=chunks,
                        conversation_history=history_list,
                    )
                    system_prompt += artifact_service.get_artifact_system_instructions()

                # Stream tokens through ArtifactStreamParser
                stream_parser = ArtifactStreamParser()
                async for token in llm_client.astream(messages=messages, system_prompt=system_prompt):
                    token_count += 1
                    full_generated_tokens.append(token)
                    event_info = stream_parser.feed_token(token)
                    if event_info["type"] == "text_delta" and event_info["content"]:
                        yield format_sse("token", ChatTokenPayload(delta=event_info["content"]))

                # Finalize parser or fallback to full text parser
                full_text = "".join(full_generated_tokens)
                parse_result = artifact_service.parse_artifacts(full_text)
                clean_text = parse_result.clean_text if parse_result.has_artifact else full_text
                extracted_artifacts = parse_result.artifacts or stream_parser.finalize()

            # ─── Stage 3: Citations Payload Event ─────────────────────────────
            if citations_data and not is_fallback:
                yield format_sse("citations", citations_data)

            # ─── Stage 4: Persist Assistant Message & Artifacts ───────────────
            assistant_msg = await message_repo.create(
                session_id=payload.session_id,
                role=MessageRole.ASSISTANT,
                content=clean_text.strip(),
                citations=citations_data if not is_fallback else [],
                has_artifact=len(extracted_artifacts) > 0,
            )

            # Persist and stream artifacts
            for art in extracted_artifacts:
                persisted_artifact = await artifact_repo.create(
                    session_id=payload.session_id,
                    artifact_type=art.artifact_type,
                    title=art.title,
                    content=art.content,
                    message_id=assistant_msg.id,
                )
                yield format_sse(
                    "artifact",
                    {
                        "id": str(persisted_artifact.id),
                        "session_id": str(payload.session_id),
                        "message_id": str(assistant_msg.id),
                        "artifact_type": art.artifact_type.value,
                        "title": art.title,
                        "content": art.content,
                    },
                )

            await db.commit()

            # ─── Stage 5: Structured Logging & Done Event ──────────────────────
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            retrieval_scores = [round(c.get("score", 0.0), 4) for c in chunks]

            logger.info(
                "Chat completion finished",
                extra={
                    "extra_data": {
                        "event": "chat_completion",
                        "session_id": str(payload.session_id),
                        "model_provider": provider.value if hasattr(provider, "value") else str(provider),
                        "model_name": target_model,
                        "latency_ms": elapsed_ms,
                        "token_count": token_count,
                        "retrieval_chunks_count": len(chunks),
                        "retrieval_scores": retrieval_scores,
                        "citations_count": len(citations_data),
                        "has_artifact": len(extracted_artifacts) > 0,
                        "is_grounded": not is_fallback,
                    }
                },
            )

            yield format_sse(
                "done",
                ChatDonePayload(
                    session_id=payload.session_id,
                    message_id=assistant_msg.id,
                    model_used=target_model,
                    citations_count=len(citations_data) if not is_fallback else 0,
                    has_artifact=len(extracted_artifacts) > 0,
                    finish_reason="stop",
                ),
            )

        except OllamaUnavailableException as exc:
            logger.warning(f"Ollama unavailable during stream: {exc}")
            yield format_sse(
                "error",
                ChatErrorPayload(
                    type="OllamaUnavailableException",
                    message=exc.message,
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                ),
            )
        except AppException as exc:
            logger.error(f"Application error during stream: {exc}")
            yield format_sse(
                "error",
                ChatErrorPayload(
                    type=exc.__class__.__name__,
                    message=exc.message,
                    status_code=exc.status_code,
                ),
            )
        except Exception as exc:
            logger.exception(f"Unexpected streaming exception: {exc}")
            yield format_sse(
                "error",
                ChatErrorPayload(
                    type="InternalServerError",
                    message="An error occurred while streaming the response.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ),
            )

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
