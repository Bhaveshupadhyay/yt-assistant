"""Unit tests for query CLI script functions."""

from unittest.mock import AsyncMock, patch
import pytest
from app.core.config import Settings
from app.core.exceptions import OllamaUnavailableException
from app.scripts.query_cli import run_rag_query, run_ship30_essay


@pytest.mark.asyncio
async def test_run_rag_query_with_mock_services() -> None:
    """Test run_rag_query executes full retrieval, citation extraction, and streaming."""
    test_settings = Settings(ANTHROPIC_API_KEY="sk-ant-test")

    with patch("app.scripts.query_cli.RAGService") as mock_rag_cls, \
         patch("app.scripts.query_cli.get_llm_client") as mock_get_llm:

        mock_rag = mock_rag_cls.return_value
        mock_rag.retrieve = AsyncMock(return_value=[
            {
                "id": "1",
                "payload": {
                    "episode_title": "Elena Verna on PLG",
                    "guest_name": "Elena Verna",
                    "guest_role": "Advisor",
                    "timestamp": "00:01:00",
                    "text": "Product-led growth drives self-serve acquisition.",
                }
            }
        ])
        mock_rag.is_fallback_needed.return_value = False
        from app.schemas.message import CitationSchema
        mock_rag.extract_citations.return_value = [
            CitationSchema(
                episode_title="Elena Verna on PLG",
                guest_name="Elena Verna",
                timestamp="00:01:00",
                snippet="Product-led growth...",
            )
        ]

        async def fake_stream(*args, **kwargs):
            yield "Elena Verna "
            yield "explains PLG."

        mock_rag.astream_query = fake_stream

        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm

        res = await run_rag_query(
            query_text="What is PLG?",
            model_name="claude-3-5-sonnet",
            top_k=1,
            stream=True,
            settings=test_settings,
        )

        assert res["query"] == "What is PLG?"
        assert res["answer"] == "Elena Verna explains PLG."
        assert len(res["citations"]) == 1


@pytest.mark.asyncio
async def test_run_rag_query_zero_hallucination_fallback() -> None:
    """Test run_rag_query handles empty retrieval with zero-hallucination fallback."""
    test_settings = Settings(ANTHROPIC_API_KEY="sk-ant-test")

    with patch("app.scripts.query_cli.RAGService") as mock_rag_cls, \
         patch("app.scripts.query_cli.get_llm_client") as mock_get_llm:

        mock_rag = mock_rag_cls.return_value
        mock_rag.retrieve = AsyncMock(return_value=[])
        mock_rag.is_fallback_needed.return_value = True
        mock_rag.get_zero_hallucination_fallback.return_value = "I could not find specific insights..."

        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm

        res = await run_rag_query(
            query_text="Unrecorded query",
            model_name="claude-3-5-sonnet",
            top_k=1,
            stream=True,
            settings=test_settings,
        )

        assert res["is_grounded"] is False
        assert "I could not find specific insights" in res["answer"]


@pytest.mark.asyncio
async def test_run_rag_query_ollama_unavailable_handling() -> None:
    """Test run_rag_query handles Ollama connection error gracefully."""
    test_settings = Settings()

    with patch("app.scripts.query_cli.RAGService") as mock_rag_cls, \
         patch("app.scripts.query_cli.get_llm_client") as mock_get_llm:

        mock_rag = mock_rag_cls.return_value
        mock_rag.retrieve = AsyncMock(return_value=[{"payload": {"text": "some text"}}])
        mock_rag.is_fallback_needed.return_value = False
        mock_rag.extract_citations.return_value = []

        async def fake_stream_error(*args, **kwargs):
            raise OllamaUnavailableException("Ollama unreachable")
            yield ""

        mock_rag.astream_query = fake_stream_error

        res = await run_rag_query(
            query_text="Explain PLG",
            model_name="llama3.2",
            stream=True,
            settings=test_settings,
        )

        assert res["type"] == "OllamaUnavailableException"


@pytest.mark.asyncio
async def test_run_ship30_essay_generation() -> None:
    """Test run_ship30_essay generates essay and structural analysis."""
    test_settings = Settings(ANTHROPIC_API_KEY="sk-ant-test")

    with patch("app.scripts.query_cli.Ship30Service") as mock_ship_cls, \
         patch("app.scripts.query_cli.get_llm_client") as mock_get_llm:

        mock_ship = mock_ship_cls.return_value

        async def fake_essay_stream(*args, **kwargs):
            yield "Hook sentence. "
            yield "Explaining points here. "
            yield "Final takeaway line."

        mock_ship.astream_essay = fake_essay_stream
        mock_ship.analyze_essay_structure.return_value = {
            "word_count": 500,
            "header_count": 3,
            "bold_bullets_count": 3,
            "has_action_checklist": True,
            "has_guest_citations": True,
        }

        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm

        res = await run_ship30_essay(
            topic="Retention Curves",
            model_name="claude-3-5-sonnet",
            top_k=2,
            stream=True,
            settings=test_settings,
        )

        assert res["topic"] == "Retention Curves"
        assert "Hook sentence" in res["essay"]
        assert res["analysis"]["has_action_checklist"] is True
