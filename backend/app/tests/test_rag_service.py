"""Unit tests for Grounded RAG Retrieval Service and zero-hallucination guard."""

from collections.abc import AsyncIterator
from typing import Any
import pytest
from app.core.config import Settings
from app.core.enums import ModelProvider
from app.schemas.message import CitationSchema
from app.services.llm.base import BaseLLMClient
from app.services.rag_service import NO_DATA_FALLBACK, RAGService


class MockVectorStore:
    """Mock vector store for testing RAG service without hitting Qdrant."""

    def __init__(self, search_results: list[dict[str, Any]] | None = None) -> None:
        self.search_results = search_results if search_results is not None else []

    def search(self, query: str, limit: int = 5, collection_name: str | None = None) -> list[dict[str, Any]]:
        return self.search_results[:limit]


class MockLLM(BaseLLMClient):
    """Mock LLM client for testing RAG generation."""

    def __init__(self, answer: str = "Elena Verna recommends a self-serve product loop.") -> None:
        super().__init__(model_name="mock-claude", provider=ModelProvider.ANTHROPIC)
        self.answer = answer
        self.last_messages: list[dict[str, str]] = []
        self.last_system_prompt: str | None = None

    async def astream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        self.last_messages = messages
        self.last_system_prompt = system_prompt
        words = self.answer.split(" ")
        for i, w in enumerate(words):
            yield w if i == 0 else " " + w

    async def check_health(self) -> bool:
        return True


@pytest.fixture
def sample_rag_chunks() -> list[dict[str, Any]]:
    """Sample chunk payloads from Qdrant search."""
    return [
        {
            "id": "chunk-1",
            "score": 0.88,
            "payload": {
                "chunk_id": "chunk-1",
                "episode_id": "elena_verna_plg",
                "episode_title": "Elena Verna on B2B Growth & PLG",
                "guest_name": "Elena Verna",
                "guest_role": "Growth Advisor",
                "timestamp": "00:04:12 - 00:08:45",
                "url": "https://youtube.com/watch?v=123",
                "text": "PLG is not a replacement for sales; it is a top-of-funnel acquisition engine.",
            },
        },
        {
            "id": "chunk-2",
            "score": 0.82,
            "payload": {
                "chunk_id": "chunk-2",
                "episode_id": "shreyas_doshi_pm",
                "episode_title": "Shreyas Doshi on High Impact PM",
                "guest_name": "Shreyas Doshi",
                "guest_role": "Product Leader",
                "timestamp": "00:10:00 - 00:15:00",
                "url": "https://youtube.com/watch?v=456",
                "text": "The LNO framework separates tasks into Leverage, Neutral, and Overhead.",
            },
        },
    ]


@pytest.mark.asyncio
async def test_rag_service_retrieve_empty_query() -> None:
    """Test RAGService returns empty list when query is blank."""
    rag = RAGService(vector_store=MockVectorStore([]))
    res = await rag.retrieve(query="   ")
    assert res == []


@pytest.mark.asyncio
async def test_rag_service_retrieve_chunks(sample_rag_chunks: list[dict[str, Any]]) -> None:
    """Test RAGService retrieve returns expected chunks."""
    rag = RAGService(vector_store=MockVectorStore(sample_rag_chunks))
    res = await rag.retrieve(query="What is PLG?", top_k=2)
    assert len(res) == 2
    assert res[0]["payload"]["guest_name"] == "Elena Verna"


def test_rag_service_extract_citations(sample_rag_chunks: list[dict[str, Any]]) -> None:
    """Test extracting verified CitationSchema models from search payloads."""
    rag = RAGService(vector_store=MockVectorStore([]))
    citations = rag.extract_citations(sample_rag_chunks)
    assert len(citations) == 2

    c1 = citations[0]
    assert isinstance(c1, CitationSchema)
    assert c1.guest_name == "Elena Verna"
    assert c1.episode_title == "Elena Verna on B2B Growth & PLG"
    assert c1.timestamp == "00:04:12 - 00:08:45"
    assert "top-of-funnel" in (c1.snippet or "")


def test_rag_service_fallback_detection(sample_rag_chunks: list[dict[str, Any]]) -> None:
    """Test is_fallback_needed identifies empty or missing chunks."""
    rag = RAGService(vector_store=MockVectorStore([]))
    assert rag.is_fallback_needed([]) is True
    assert rag.is_fallback_needed([{"payload": {"text": ""}}]) is True
    assert rag.is_fallback_needed(sample_rag_chunks) is False


def test_rag_service_prompt_construction(sample_rag_chunks: list[dict[str, Any]]) -> None:
    """Test system prompt and user context formatting enforce grounding rules."""
    rag = RAGService(vector_store=MockVectorStore([]))
    sys_prompt = rag.build_grounding_system_prompt()
    assert "The Lenny Growth Assistant" in sys_prompt
    assert "STRICT TRANSCRIPT GROUNDING" in sys_prompt
    assert "ZERO-HALLUCINATION GUARD" in sys_prompt
    assert NO_DATA_FALLBACK in sys_prompt

    context_prompt = rag.build_context_prompt("How does PLG work?", sample_rag_chunks)
    assert "Elena Verna" in context_prompt
    assert "00:04:12 - 00:08:45" in context_prompt
    assert "How does PLG work?" in context_prompt


@pytest.mark.asyncio
async def test_rag_service_query_grounded_success(sample_rag_chunks: list[dict[str, Any]]) -> None:
    """Test complete grounded RAG query with valid chunks returns citations and answer."""
    rag = RAGService(vector_store=MockVectorStore(sample_rag_chunks))
    mock_llm = MockLLM(answer="Elena Verna states that PLG acts as an acquisition engine.")

    result = await rag.query(query="Explain PLG", llm_client=mock_llm, top_k=2)
    assert result["is_grounded"] is True
    assert "Elena Verna" in result["answer"]
    assert len(result["citations"]) == 2
    assert len(result["retrieved_chunks"]) == 2


@pytest.mark.asyncio
async def test_rag_service_zero_hallucination_guard_on_empty() -> None:
    """Test zero-hallucination guard immediately returns fallback without executing LLM."""
    rag = RAGService(vector_store=MockVectorStore([]))
    mock_llm = MockLLM(answer="I am hallucinating fake advice!")

    result = await rag.query(query="Some obscure unrecorded topic", llm_client=mock_llm)
    assert result["is_grounded"] is False
    assert result["answer"] == NO_DATA_FALLBACK
    assert result["citations"] == []
    assert mock_llm.last_messages == []  # Verifies LLM was NOT called!


@pytest.mark.asyncio
async def test_rag_service_astream_query(sample_rag_chunks: list[dict[str, Any]]) -> None:
    """Test astream_query yields tokens for grounded matches and fallback for empty matches."""
    rag = RAGService(vector_store=MockVectorStore(sample_rag_chunks))
    mock_llm = MockLLM(answer="PLG is powerful.")

    streamed = []
    async for tok in rag.astream_query("PLG", llm_client=mock_llm):
        streamed.append(tok)
    assert "".join(streamed) == "PLG is powerful."

    # Test stream on empty
    rag_empty = RAGService(vector_store=MockVectorStore([]))
    empty_streamed = []
    async for tok in rag_empty.astream_query("Quantum Physics", llm_client=mock_llm):
        empty_streamed.append(tok)
    assert "".join(empty_streamed) == NO_DATA_FALLBACK


def test_is_conversational_turn_detection() -> None:
    """Test is_conversational_turn correctly recognizes pleasantries and acknowledgments."""
    from app.services.rag_service import is_conversational_turn

    # True cases
    assert is_conversational_turn("got it") is True
    assert is_conversational_turn("got it!") is True
    assert is_conversational_turn("Got it.") is True
    assert is_conversational_turn("thanks") is True
    assert is_conversational_turn("thank you so much") is True
    assert is_conversational_turn("ok") is True
    assert is_conversational_turn("cool") is True
    assert is_conversational_turn("sounds good") is True
    assert is_conversational_turn("hello") is True
    assert is_conversational_turn("hi") is True
    assert is_conversational_turn("great!") is True

    # False cases (substantive queries)
    assert is_conversational_turn("what does Elena Verna say about PLG?") is False
    assert is_conversational_turn("Explain Brian Balfour's 4 growth loops") is False
    assert is_conversational_turn("got it, but how do I price my SaaS product?") is False
    assert is_conversational_turn("Write a Ship 30 essay on retention") is False


def test_build_conversational_messages() -> None:
    """Test build_conversational_messages creates appropriate system prompt and history."""
    rag = RAGService(vector_store=MockVectorStore([]))
    history = [{"role": "user", "content": "How do I do PLG?"}, {"role": "assistant", "content": "Elena Verna says..."}]
    sys_prompt, messages = rag.build_conversational_messages(query="got it", conversation_history=history)

    assert "Lenny Growth Assistant" in sys_prompt
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "got it"
