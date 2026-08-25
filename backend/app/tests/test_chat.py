"""Automated pytest suite for streaming Chat API with Server-Sent Events (SSE) (Task 4.3 & Task 5.2)."""

from collections.abc import AsyncIterator
import json
from typing import Any
from unittest.mock import AsyncMock, patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings
from app.core.dependencies import get_rag_service
from app.core.enums import ModelName, ModelProvider
from app.core.exceptions import OllamaUnavailableException
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.message_repository import MessageRepository
from app.services.llm.base import BaseLLMClient
from app.services.rag_service import NO_DATA_FALLBACK, RAGService


class MockStreamingLLM(BaseLLMClient):
    """Mock LLM that streams predefined tokens."""

    def __init__(self, stream_chunks: list[str]) -> None:
        super().__init__(model_name="mock-claude", provider=ModelProvider.ANTHROPIC)
        self.stream_chunks = stream_chunks

    async def astream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        for chunk in self.stream_chunks:
            yield chunk

    async def check_health(self) -> bool:
        return True


class MockFailingLLM(BaseLLMClient):
    """Mock LLM that raises an exception during streaming."""

    def __init__(self, exception_to_raise: Exception) -> None:
        super().__init__(model_name="mock-failing", provider=ModelProvider.OLLAMA)
        self.exception = exception_to_raise

    async def astream(self, messages: list[dict[str, str]], system_prompt: str | None = None, **kwargs: Any) -> AsyncIterator[str]:
        raise self.exception
        yield ""  # Make it an async generator

    async def check_health(self) -> bool:
        return False


def parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
    """Helper to parse raw SSE text stream into structured event objects."""
    events = []
    current_event = None
    current_data = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            if current_event and current_data:
                data_str = "\n".join(current_data)
                try:
                    parsed_json = json.loads(data_str)
                except json.JSONDecodeError:
                    parsed_json = data_str
                events.append({"event": current_event, "data": parsed_json})
            current_event = None
            current_data = []
            continue

        if line.startswith("event:"):
            current_event = line.replace("event:", "").strip()
        elif line.startswith("data:"):
            current_data.append(line.replace("data:", "").strip())

    if current_event and current_data:
        data_str = "\n".join(current_data)
        try:
            parsed_json = json.loads(data_str)
        except json.JSONDecodeError:
            parsed_json = data_str
        events.append({"event": current_event, "data": parsed_json})

    return events


@pytest.fixture
def mock_retrieval_chunks() -> list[dict[str, Any]]:
    """Sample chunk payloads for testing grounded retrieval."""
    return [
        {
            "id": "chunk-101",
            "score": 0.92,
            "payload": {
                "chunk_id": "chunk-101",
                "episode_id": "elena_verna_plg",
                "episode_title": "Elena Verna on B2B Growth & PLG",
                "guest_name": "Elena Verna",
                "guest_role": "Growth Advisor",
                "timestamp": "00:04:12 - 00:08:45",
                "url": "https://youtube.com/watch?v=123",
                "text": "Product-led growth uses the product as the primary vehicle for customer acquisition and retention.",
            },
        }
    ]


@pytest.mark.asyncio
async def test_stream_chat_sse_grounded_response(
    async_client: AsyncClient,
    mock_retrieval_chunks: list[dict[str, Any]],
    db_session: AsyncSession,
):
    """Verify full SSE lifecycle: status -> token streaming -> citations -> done, with DB persistence."""
    # 1. Create session
    create_resp = await async_client.post("/api/v1/sessions", json={"title": "PLG Chat Session"})
    session_id = create_resp.json()["id"]

    mock_llm = MockStreamingLLM(stream_chunks=["Product-Led ", "Growth ", "is ", "strategic."])

    with patch("app.api.v1.chat.get_llm_client", return_value=mock_llm):
        with patch.object(RAGService, "retrieve", AsyncMock(return_value=mock_retrieval_chunks)):
            chat_payload = {
                "session_id": session_id,
                "message": "How does PLG work according to Elena Verna?",
                "model": ModelName.CLAUDE_3_5_SONNET.value,
            }

            resp = await async_client.post("/api/v1/chat", json=chat_payload)
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

            events = parse_sse_events(resp.text)
            event_types = [e["event"] for e in events]

            # Verify event sequence
            assert "status" in event_types
            assert "token" in event_types
            assert "citations" in event_types
            assert "done" in event_types

            # Verify status events
            status_events = [e for e in events if e["event"] == "status"]
            assert any(s["data"].get("stage") == "retrieval" for s in status_events)
            assert any(s["data"].get("stage") == "generation" for s in status_events)

            # Verify token text
            tokens = [e["data"]["delta"] for e in events if e["event"] == "token"]
            assert "".join(tokens) == "Product-Led Growth is strategic."

            # Verify citations event
            citations_event = next(e for e in events if e["event"] == "citations")
            assert len(citations_event["data"]) == 1
            assert citations_event["data"][0]["guest_name"] == "Elena Verna"
            assert citations_event["data"][0]["episode_title"] == "Elena Verna on B2B Growth & PLG"

            # Verify done event
            done_event = next(e for e in events if e["event"] == "done")
            assert done_event["data"]["session_id"] == session_id
            assert done_event["data"]["finish_reason"] == "stop"

            # Verify DB persistence
            msg_repo = MessageRepository(db_session)
            history = await msg_repo.get_by_session_id(uuid.UUID(session_id))
            assert len(history) == 2
            assert history[0].role.value == "user"
            assert history[0].content == "How does PLG work according to Elena Verna?"
            assert history[1].role.value == "assistant"
            assert history[1].content == "Product-Led Growth is strategic."
            assert len(history[1].citations) == 1


@pytest.mark.asyncio
async def test_stream_chat_sse_with_artifact_generation(
    async_client: AsyncClient,
    mock_retrieval_chunks: list[dict[str, Any]],
    db_session: AsyncSession,
):
    """Verify that when an artifact tag is in the LLM output, an 'artifact' event is emitted and persisted."""
    create_resp = await async_client.post("/api/v1/sessions", json={"title": "Artifact Session"})
    session_id = create_resp.json()["id"]

    artifact_html = "<!DOCTYPE html><html><body><h1>PLG Retention Matrix</h1></body></html>"
    raw_llm_stream = [
        "Here is the interactive calculator:\n\n",
        '<artifact type="html" title="PLG Retention Matrix">\n',
        artifact_html,
        "\n</artifact>",
    ]
    mock_llm = MockStreamingLLM(stream_chunks=raw_llm_stream)

    with patch("app.api.v1.chat.get_llm_client", return_value=mock_llm):
        with patch.object(RAGService, "retrieve", AsyncMock(return_value=mock_retrieval_chunks)):
            chat_payload = {
                "session_id": session_id,
                "message": "Generate a PLG retention calculator HTML artifact.",
            }

            resp = await async_client.post("/api/v1/chat", json=chat_payload)
            assert resp.status_code == 200

            events = parse_sse_events(resp.text)
            artifact_events = [e for e in events if e["event"] == "artifact"]
            assert len(artifact_events) == 1
            art_data = artifact_events[0]["data"]
            assert art_data["title"] == "PLG Retention Matrix"
            assert art_data["artifact_type"] == "html"
            assert "PLG Retention Matrix" in art_data["content"]

            # Verify artifact persistence in DB
            art_repo = ArtifactRepository(db_session)
            db_artifacts = await art_repo.get_by_session_id(uuid.UUID(session_id))
            assert len(db_artifacts) == 1
            assert db_artifacts[0].title == "PLG Retention Matrix"


@pytest.mark.asyncio
async def test_stream_chat_zero_hallucination_fallback(
    async_client: AsyncClient,
):
    """Verify zero-hallucination guard triggers when no relevant transcripts exist."""
    create_resp = await async_client.post("/api/v1/sessions", json={"title": "Fallback Session"})
    session_id = create_resp.json()["id"]

    with patch.object(RAGService, "retrieve", AsyncMock(return_value=[])):
        chat_payload = {
            "session_id": session_id,
            "message": "What did Lenny say about quantum mechanics?",
        }

        resp = await async_client.post("/api/v1/chat", json=chat_payload)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        tokens = [e["data"]["delta"] for e in events if e["event"] == "token"]
        streamed_text = "".join(tokens).strip()

        assert streamed_text == NO_DATA_FALLBACK
        # Verify NO citations event is yielded for fallback
        assert not any(e["event"] == "citations" for e in events)


@pytest.mark.asyncio
async def test_stream_chat_nonexistent_session_raises_404(
    async_client: AsyncClient,
):
    """Verify POST /api/v1/chat with invalid session_id returns 404."""
    random_id = uuid.uuid4()
    chat_payload = {
        "session_id": str(random_id),
        "message": "Hello",
    }
    resp = await async_client.post("/api/v1/chat", json=chat_payload)
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["type"] == "SessionNotFoundException"


@pytest.mark.asyncio
async def test_stream_chat_ollama_offline_emits_error_event(
    async_client: AsyncClient,
    mock_retrieval_chunks: list[dict[str, Any]],
):
    """Verify that when Ollama is offline, an SSE 'error' event with 503 is yielded."""
    create_resp = await async_client.post("/api/v1/sessions", json={"title": "Offline Ollama Session"})
    session_id = create_resp.json()["id"]

    mock_failing_llm = MockFailingLLM(
        exception_to_raise=OllamaUnavailableException()
    )

    with patch("app.api.v1.chat.get_llm_client", return_value=mock_failing_llm):
        with patch.object(RAGService, "retrieve", AsyncMock(return_value=mock_retrieval_chunks)):
            chat_payload = {
                "session_id": session_id,
                "message": "Explain growth loops",
                "model": ModelName.LLAMA_3_2.value,
            }

            resp = await async_client.post("/api/v1/chat", json=chat_payload)
            assert resp.status_code == 200

            events = parse_sse_events(resp.text)
            error_events = [e for e in events if e["event"] == "error"]
            assert len(error_events) == 1
            err_data = error_events[0]["data"]
            assert err_data["type"] == "OllamaUnavailableException"
            assert err_data["status_code"] == 503
