"""Grounded RAG retrieval service with hybrid search, strict attribution, and zero-hallucination guard."""

import asyncio
from collections.abc import AsyncGenerator
import logging
from typing import Any
from app.core.config import Settings, get_settings
from app.schemas.message import CitationSchema
from app.services.llm.base import BaseLLMClient
from app.services.vector_store import HybridVectorStore

logger = logging.getLogger(__name__)

# Standard zero-hallucination fallback message defined in project domain rules
NO_DATA_FALLBACK = (
    "I could not find specific insights or discussions on this topic within the available Lenny's Podcast transcripts."
)


class RAGService:
    """Enterprise RAG Service combining dense + sparse hybrid search with strict transcript grounding."""

    def __init__(
        self,
        vector_store: HybridVectorStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize RAGService.

        Args:
            vector_store: Optional pre-configured HybridVectorStore instance.
            settings: Optional application settings.
        """
        self.settings = settings or get_settings()
        self.vector_store = vector_store or HybridVectorStore(settings=self.settings)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search (Dense + SPLADE Sparse RRF) asynchronously over Qdrant.

        Args:
            query: User's search query.
            top_k: Maximum number of relevant chunks to retrieve.
            collection_name: Optional collection name override.

        Returns:
            list[dict[str, Any]]: List of matching results with score and metadata payload.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        # Run vector embedding and Qdrant RRF query in a thread pool to avoid blocking the event loop
        results = await asyncio.to_thread(
            self.vector_store.search,
            query=clean_query,
            limit=top_k,
            collection_name=collection_name,
        )
        return results

    def extract_citations(self, search_results: list[dict[str, Any]]) -> list[CitationSchema]:
        """Convert raw Qdrant search result payloads into verified CitationSchema objects.

        Args:
            search_results: Raw search hits from retrieve().

        Returns:
            list[CitationSchema]: Structured citation list.
        """
        citations: list[CitationSchema] = []
        seen_keys: set[str] = set()

        for res in search_results:
            payload = res.get("payload", {})
            if not payload:
                continue

            episode_title = payload.get("episode_title", "Lenny's Podcast")
            guest_name = payload.get("guest_name", "Lenny Rachitsky")
            timestamp = payload.get("timestamp", "00:00:00")
            unique_key = f"{episode_title}_{guest_name}_{timestamp}"

            if unique_key in seen_keys:
                continue
            seen_keys.add(unique_key)

            # Extract snippet from text
            text = payload.get("text", "")
            snippet = text[:300] + "..." if len(text) > 300 else text

            citation = CitationSchema(
                episode_title=episode_title,
                guest_name=guest_name,
                guest_role=payload.get("guest_role"),
                timestamp=timestamp,
                youtube_url=payload.get("url"),
                snippet=snippet,
            )
            citations.append(citation)

        return citations

    def is_fallback_needed(self, retrieved_chunks: list[dict[str, Any]]) -> bool:
        """Evaluate if retrieved chunks are empty or below relevance threshold.

        Args:
            retrieved_chunks: Results from hybrid search.

        Returns:
            bool: True if no data is available to answer the query.
        """
        if not retrieved_chunks:
            return True

        # Check if at least one chunk has valid text content
        has_content = any(
            bool(r.get("payload", {}).get("text", "").strip()) for r in retrieved_chunks
        )
        return not has_content

    def get_zero_hallucination_fallback(self) -> str:
        """Return the exact zero-hallucination fallback string."""
        return NO_DATA_FALLBACK

    def build_grounding_system_prompt(self) -> str:
        """Construct the strict system prompt enforcing transcript attribution and zero hallucination."""
        return (
            "You are The Lenny Growth Assistant, an Executive Growth and Product Advisor for "
            "product managers, growth leads, and founders.\n\n"
            "🛡️ CORE GROUNDING & ATTRIBUTION RULES (MANDATORY):\n"
            "1. STRICT TRANSCRIPT GROUNDING: All tactical frameworks, benchmarks, metrics, and strategic advice "
            "MUST be derived directly from the provided podcast transcript excerpts.\n"
            "2. EXPLICIT CITATIONS: For every framework, rule, or claim, you MUST explicitly cite the specific "
            "Guest Name and Episode Title (e.g., Elena Verna in 'B2B Growth and Product-Led Sales' [00:04:12]).\n"
            "3. ZERO-HALLUCINATION GUARD: If the provided excerpts do not contain sufficient information to answer "
            "the user's question, you MUST reply ONLY with this exact sentence:\n"
            f'"{NO_DATA_FALLBACK}"\n'
            "Never guess, invent statistics, extrapolate unstated facts, or offer generic corporate fluff.\n"
            "4. OPERATOR TONE: Be direct, structured, and actionable. Use bullet points with bold lead-ins for key insights."
        )

    def build_context_prompt(self, query: str, retrieved_chunks: list[dict[str, Any]]) -> str:
        """Format retrieved chunks into structured context blocks for the user prompt.

        Args:
            query: User's question.
            retrieved_chunks: Top matching chunks from Qdrant.

        Returns:
            str: Formatted context block with source metadata.
        """
        if not retrieved_chunks:
            return f"User Question: {query}\n\n[No matching transcript excerpts found in knowledge base]"

        context_parts = ["### Relevant Transcripts from Lenny's Podcast:\n"]
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            payload = chunk.get("payload", {})
            guest = payload.get("guest_name", "Unknown Guest")
            role = payload.get("guest_role", "")
            title = payload.get("episode_title", "Lenny's Podcast")
            timestamp = payload.get("timestamp", "00:00:00")
            url = payload.get("url", "")
            text = payload.get("text", "").strip()

            role_str = f" ({role})" if role else ""
            url_str = f"\nURL: {url}" if url else ""

            context_parts.append(
                f"--- [Excerpt {idx}] ---\n"
                f"Guest: {guest}{role_str}\n"
                f"Episode: {title}\n"
                f"Timestamp: {timestamp}{url_str}\n"
                f"Content:\n{text}\n"
            )

        context_parts.append(
            f"--- End of Excerpts ---\n\n"
            f"User Question: {query}\n\n"
            "Synthesize a grounded, structured answer referencing the guest names and episode titles above. "
            "If the excerpts do not contain the answer, return the fallback message verbatim."
        )
        return "\n".join(context_parts)

    def build_grounded_messages(
        self,
        query: str,
        retrieved_chunks: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[dict[str, str]]]:
        """Construct the system prompt and conversation messages list for the LLM.

        Args:
            query: Current user query.
            retrieved_chunks: Retrieved semantic chunks.
            conversation_history: Optional prior messages in the session.

        Returns:
            tuple[str, list[dict[str, str]]]: System prompt and messages list.
        """
        system_prompt = self.build_grounding_system_prompt()
        context_user_message = self.build_context_prompt(query, retrieved_chunks)

        messages: list[dict[str, str]] = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": context_user_message})
        return system_prompt, messages

    async def query(
        self,
        query: str,
        llm_client: BaseLLMClient,
        top_k: int = 5,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Execute a complete grounded RAG query against the vector store and LLM client.

        Args:
            query: User's question.
            llm_client: LLM client to use for generation.
            top_k: Number of chunks to retrieve.
            conversation_history: Optional prior messages.

        Returns:
            dict[str, Any]: Response dictionary with 'answer', 'citations', 'retrieved_chunks', 'is_grounded'.
        """
        chunks = await self.retrieve(query=query, top_k=top_k)

        # Zero-hallucination guard: If no chunks retrieved, return fallback immediately
        if self.is_fallback_needed(chunks):
            return {
                "answer": self.get_zero_hallucination_fallback(),
                "citations": [],
                "retrieved_chunks": [],
                "is_grounded": False,
            }

        citations = self.extract_citations(chunks)
        system_prompt, messages = self.build_grounded_messages(
            query=query,
            retrieved_chunks=chunks,
            conversation_history=conversation_history,
        )

        answer = await llm_client.acomplete(
            messages=messages,
            system_prompt=system_prompt,
        )

        return {
            "answer": answer.strip(),
            "citations": [c.model_dump() for c in citations],
            "retrieved_chunks": chunks,
            "is_grounded": True,
        }

    async def astream_query(
        self,
        query: str,
        llm_client: BaseLLMClient,
        top_k: int = 5,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens for a grounded RAG query.

        Yields:
            str: Generated tokens.
        """
        chunks = await self.retrieve(query=query, top_k=top_k)

        if self.is_fallback_needed(chunks):
            yield self.get_zero_hallucination_fallback()
            return

        system_prompt, messages = self.build_grounded_messages(
            query=query,
            retrieved_chunks=chunks,
            conversation_history=conversation_history,
        )

        async for token in llm_client.astream(
            messages=messages,
            system_prompt=system_prompt,
        ):
            yield token
