"""Dedicated 'Ship 30 for 30' Essay Generation Skill Service."""

from collections.abc import AsyncGenerator
import logging
import re
from typing import Any
from app.schemas.message import CitationSchema
from app.services.llm.base import BaseLLMClient
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class Ship30Service:
    """Specialized skill engine for generating ~1,250-word atomic 'Ship 30 for 30' essays grounded in Lenny transcripts."""

    def __init__(self, rag_service: RAGService | None = None) -> None:
        """Initialize Ship30Service.

        Args:
            rag_service: Optional RAGService instance for transcript retrieval.
        """
        self.rag_service = rag_service

    def build_ship30_system_prompt(self) -> str:
        """Construct the prompt pipeline instructions for Ship 30 for 30 writing style."""
        return (
            "You are a World-Class Executive Growth Strategist and Master Essayist trained in the 'Ship 30 for 30' "
            "atomic writing methodology.\n\n"
            "Your mission: Write an authoritative, publication-ready growth memo/essay (~1,250 words) grounded strictly "
            "in the provided insights from Lenny's Podcast transcripts.\n\n"
            "✍️ NON-NEGOTIABLE 'SHIP 30 FOR 30' WRITING STANDARDS:\n\n"
            "1. THE MAGNETIC HOOK:\n"
            "   - Open immediately with a high-friction problem statement, counterintuitive operator insight, "
            "or bold contrarian premise.\n"
            "   - Do NOT start with greeting or throat-clearing intro (e.g. 'In this essay, we will explore...'). Dive straight into the fire.\n\n"
            "2. PACING & CADENCE (THE 1-3-1 STRUCTURE):\n"
            "   - Use the 1-3-1 sentence structure throughout:\n"
            "     • 1 punchy single-line sentence.\n"
            "     • A 3-sentence tight explanatory/contextual block.\n"
            "     • 1 punchy takeaway line.\n"
            "   - Short paragraphs only (maximum 2-3 sentences each). No walls of text.\n\n"
            "3. VISUAL BOLDING & HIGH SKIMMABILITY:\n"
            "   - Use clear `##` and `###` headers for logical sections.\n"
            "   - Bullet points MUST use **bolded lead-in phrases** (first 2-4 words bolded) for rapid executive scanning.\n\n"
            "4. TARGET LENGTH & DENSITY:\n"
            "   - Target length: ~1,250 words.\n"
            "   - Maximum tactical density with zero corporate fluff or filler.\n\n"
            "5. DEEP TRANSCRIPT GROUNDING & ATTRIBUTION:\n"
            "   - Weave specific guest quotes, frameworks, and battle-tested lessons directly into every section.\n"
            "   - Explicitly cite the Guest Name and Episode Title (e.g., Elena Verna in 'B2B Growth & PLG').\n\n"
            "6. ACTIONABLE 3-STEP CLOSING CHECKLIST:\n"
            "   - Conclude the essay with a dedicated section: `### 3-Step Action Checklist for Tomorrow Morning`.\n"
            "   - Provide 3 concrete, numbered, immediate action items that a PM, Growth Lead, or Founder can execute right away.\n\n"
            "7. ARTIFACT PACKAGING:\n"
            "   - Encapsulate the full completed essay inside `<artifact type=\"markdown\" title=\"Ship 30: [Topic]\">` tags.\n"
            "   - Provide a 1-sentence executive summary before opening the `<artifact>` tag."
        )

    def build_ship30_user_prompt(
        self,
        topic: str,
        context_chunks: list[dict[str, Any]] | None = None,
        target_audience: str = "Product Managers, Growth Leads, and Founders",
    ) -> str:
        """Format the user prompt including topic and transcript context blocks.

        Args:
            topic: Core topic or prompt for the essay.
            context_chunks: Retrieved semantic chunks from Lenny transcripts.
            target_audience: Target reader persona.

        Returns:
            str: Formatted user prompt.
        """
        prompt_parts: list[str] = [
            f"Topic: {topic}\n",
            f"Target Audience: {target_audience}\n",
        ]

        if context_chunks:
            prompt_parts.append("### Grounding Context from Lenny's Podcast:\n")
            for idx, chunk in enumerate(context_chunks, start=1):
                payload = chunk.get("payload", {})
                guest = payload.get("guest_name", "Lenny Guest")
                role = payload.get("guest_role", "")
                title = payload.get("episode_title", "Lenny's Podcast")
                timestamp = payload.get("timestamp", "00:00:00")
                text = payload.get("text", "").strip()

                prompt_parts.append(
                    f"--- [Source {idx}: {guest} ({role}) | {title} | {timestamp}] ---\n"
                    f"{text}\n"
                )
            prompt_parts.append("--- End of Sources ---\n")
        else:
            prompt_parts.append("[Note: Synthesize using core growth frameworks and principles]\n")

        prompt_parts.append(
            "Write a complete, high-impact 'Ship 30 for 30' essay (~1,250 words) on this topic. "
            "Adhere strictly to the 1-3-1 cadence, magnetic hook, bolded bullet lead-ins, guest citations, "
            "and end with the 3-step action checklist."
        )

        return "\n".join(prompt_parts)

    def analyze_essay_structure(self, essay_text: str) -> dict[str, Any]:
        """Analyze a generated Ship 30 essay against the style standards.

        Args:
            essay_text: The complete text of the generated essay.

        Returns:
            dict[str, Any]: Metrics on word count, bolded items, headers, checklist, citations.
        """
        words = essay_text.split()
        word_count = len(words)

        headers = re.findall(r"^#{2,4}\s+.+$", essay_text, re.MULTILINE)
        bold_bullets = re.findall(r"^[\*\-]\s+\*\*[^*]+\*\*", essay_text, re.MULTILINE)
        has_checklist = bool(
            re.search(r"3-step|action checklist|checklist for tomorrow|action items", essay_text, re.IGNORECASE)
        )
        has_citations = bool(re.search(r"in \"|\bin '|\[\d{2}:\d{2}", essay_text))

        return {
            "word_count": word_count,
            "target_word_count": 1250,
            "header_count": len(headers),
            "bold_bullets_count": len(bold_bullets),
            "has_action_checklist": has_checklist,
            "has_guest_citations": has_citations,
            "meets_length_criteria": word_count >= 300,  # Minimum substantive threshold
        }

    async def generate_essay(
        self,
        topic: str,
        llm_client: BaseLLMClient,
        rag_service: RAGService | None = None,
        top_k: int = 5,
        target_audience: str = "Product Managers, Growth Leads, and Founders",
    ) -> dict[str, Any]:
        """Generate a complete grounded Ship 30 for 30 essay.

        Args:
            topic: Essay topic.
            llm_client: LLM client for generation.
            rag_service: Optional RAG service override.
            top_k: Number of transcript chunks to retrieve.
            target_audience: Target reader persona.

        Returns:
            dict[str, Any]: Generated essay text, citations, and structural analysis.
        """
        service = rag_service or self.rag_service
        context_chunks: list[dict[str, Any]] = []
        citations: list[CitationSchema] = []

        if service:
            context_chunks = await service.retrieve(query=topic, top_k=top_k)
            citations = service.extract_citations(context_chunks)

        system_prompt = self.build_ship30_system_prompt()
        user_prompt = self.build_ship30_user_prompt(
            topic=topic,
            context_chunks=context_chunks,
            target_audience=target_audience,
        )

        messages = [{"role": "user", "content": user_prompt}]
        essay_content = await llm_client.acomplete(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=4096,
        )

        analysis = self.analyze_essay_structure(essay_content)

        return {
            "topic": topic,
            "essay": essay_content.strip(),
            "citations": [c.model_dump() for c in citations],
            "word_count": analysis["word_count"],
            "analysis": analysis,
            "model_used": llm_client.model_name,
            "provider": llm_client.provider.value,
        }

    async def astream_essay(
        self,
        topic: str,
        llm_client: BaseLLMClient,
        rag_service: RAGService | None = None,
        top_k: int = 5,
        target_audience: str = "Product Managers, Growth Leads, and Founders",
    ) -> AsyncGenerator[str, None]:
        """Stream tokens for a Ship 30 for 30 essay.

        Yields:
            str: Generated tokens.
        """
        service = rag_service or self.rag_service
        context_chunks: list[dict[str, Any]] = []

        if service:
            context_chunks = await service.retrieve(query=topic, top_k=top_k)

        system_prompt = self.build_ship30_system_prompt()
        user_prompt = self.build_ship30_user_prompt(
            topic=topic,
            context_chunks=context_chunks,
            target_audience=target_audience,
        )

        messages = [{"role": "user", "content": user_prompt}]
        async for token in llm_client.astream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=4096,
        ):
            yield token
