"""Unit tests for dedicated Ship 30 for 30 essay generation skill service."""

from typing import Any
import pytest
from app.core.enums import ModelProvider
from app.services.llm.base import BaseLLMClient
from app.services.rag_service import RAGService
from app.services.ship30_service import Ship30Service


class MockLLM(BaseLLMClient):
    """Mock LLM for Ship 30 essay generation."""

    def __init__(self, essay_text: str) -> None:
        super().__init__(model_name="mock-model", provider=ModelProvider.ANTHROPIC)
        self.essay_text = essay_text

    async def astream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        for word in self.essay_text.split(" "):
            yield word + " "

    async def check_health(self) -> bool:
        return True


class MockVectorStore:
    """Mock vector store providing sample chunks."""

    def search(self, query: str, limit: int = 5, collection_name: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "id": "chunk-plg",
                "score": 0.9,
                "payload": {
                    "episode_title": "Elena Verna on PLG",
                    "guest_name": "Elena Verna",
                    "guest_role": "Growth Advisor",
                    "timestamp": "00:02:30",
                    "url": "https://youtube.com/watch?v=plg",
                    "text": "PLG requires product loops that self-perpetuate user acquisition and monetization.",
                },
            }
        ]


SAMPLE_WELL_STRUCTURED_ESSAY = """
Most founders build product-led growth completely backwards.

They treat self-serve as a cheaper sales team instead of a distribution flywheel. When users hit friction, they throw SDRs at the problem. This breaks the compounding feedback loop that makes PLG defensible in the first place.

Your product must be the primary driver of acquisition, retention, and expansion.

## The Elena Verna Framework for Compounding Loops

As Elena Verna highlighted in "Elena Verna on PLG" [00:02:30], top-of-funnel velocity without activation is just vanity churn.

* **Frictionless Onboarding:** Remove credit card walls before the core 'aha' moment.
* **Usage-Based Expansion:** Trigger monetization based on value consumption, not arbitrary seat limits.
* **Feedback-Driven Iteration:** Let drop-off telemetry dictate weekly sprint priorities.

## The Shift from Sales-Led to Hybrid

Sales should amplify product loops, not rescue broken onboarding flows.

### 3-Step Action Checklist for Tomorrow Morning

1. **Audit Time-to-Value:** Instrument exact minutes from signup to first core action.
2. **Eliminate Activation Gates:** Remove mandatory forms that gate initial user discovery.
3. **Map the Natural Expansion Trigger:** Identify which feature triggers organic upgrades.
"""


def test_ship30_service_prompt_construction() -> None:
    """Test Ship30Service system prompt specifies all required writing principles."""
    service = Ship30Service()
    sys_prompt = service.build_ship30_system_prompt()

    assert "Ship 30 for 30" in sys_prompt
    assert "THE MAGNETIC HOOK" in sys_prompt
    assert "THE 1-3-1 STRUCTURE" in sys_prompt
    assert "VISUAL BOLDING" in sys_prompt
    assert "3-Step Action Checklist" in sys_prompt
    assert "1,250 words" in sys_prompt


def test_ship30_service_user_prompt_with_context() -> None:
    """Test Ship30Service formats user prompt including retrieved context."""
    service = Ship30Service()
    chunks = [
        {
            "payload": {
                "guest_name": "Elena Verna",
                "guest_role": "Growth Advisor",
                "episode_title": "Elena Verna on PLG",
                "timestamp": "00:05:00",
                "text": "Self-serve loops compound over time.",
            }
        }
    ]
    user_prompt = service.build_ship30_user_prompt(topic="PLG Strategy", context_chunks=chunks)
    assert "Topic: PLG Strategy" in user_prompt
    assert "Elena Verna" in user_prompt
    assert "Self-serve loops compound over time." in user_prompt


def test_ship30_structure_analysis() -> None:
    """Test analyze_essay_structure correctly assesses formatting markers."""
    service = Ship30Service()
    analysis = service.analyze_essay_structure(SAMPLE_WELL_STRUCTURED_ESSAY)

    assert analysis["header_count"] >= 2
    assert analysis["bold_bullets_count"] >= 3
    assert analysis["has_action_checklist"] is True
    assert analysis["has_guest_citations"] is True
    assert analysis["word_count"] > 100


@pytest.mark.asyncio
async def test_ship30_generate_essay_end_to_end() -> None:
    """Test generate_essay returns structured essay result with citations."""
    rag_service = RAGService(vector_store=MockVectorStore())
    service = Ship30Service(rag_service=rag_service)
    mock_llm = MockLLM(essay_text=SAMPLE_WELL_STRUCTURED_ESSAY)

    result = await service.generate_essay(
        topic="How to build PLG loops",
        llm_client=mock_llm,
        top_k=1,
    )

    assert result["topic"] == "How to build PLG loops"
    assert "Elena Verna" in result["essay"]
    assert len(result["citations"]) == 1
    assert result["citations"][0]["guest_name"] == "Elena Verna"
    assert result["analysis"]["has_action_checklist"] is True


@pytest.mark.asyncio
async def test_ship30_astream_essay() -> None:
    """Test astream_essay yields tokens in sequence."""
    rag_service = RAGService(vector_store=MockVectorStore())
    service = Ship30Service(rag_service=rag_service)
    mock_llm = MockLLM(essay_text="Punchy hook. Explanatory sentences here. Punchy line.")

    tokens = []
    async for t in service.astream_essay(topic="Growth Loops", llm_client=mock_llm):
        tokens.append(t)

    assert "".join(tokens).strip() == "Punchy hook. Explanatory sentences here. Punchy line."
