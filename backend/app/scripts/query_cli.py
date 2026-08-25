"""CLI utility to query the Grounded RAG Service, generate Ship 30 for 30 essays, and test LLM providers."""

import argparse
import asyncio
import json
import sys
import time
from typing import Any
from app.core.config import Settings, get_settings
from app.core.enums import ModelName
from app.core.exceptions import OllamaUnavailableException
from app.services.artifact_service import ArtifactService
from app.services.llm.factory import get_llm_client
from app.services.rag_service import RAGService
from app.services.ship30_service import Ship30Service


async def run_rag_query(
    query_text: str,
    model_name: str,
    top_k: int = 5,
    stream: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Execute a grounded RAG query using the specified model provider."""
    cfg = settings or get_settings()
    rag_service = RAGService(settings=cfg)
    artifact_service = ArtifactService()

    print(f"\n🔍 Searching knowledge base for: '{query_text}' (model: {model_name}, top_k={top_k})...")
    start_time = time.perf_counter()

    try:
        llm = get_llm_client(model_name=model_name, settings=cfg)
    except Exception as exc:
        print(f"❌ Failed to initialize LLM client: {exc}")
        return {"error": str(exc)}

    retrieval_start = time.perf_counter()
    chunks = await rag_service.retrieve(query=query_text, top_k=top_k)
    retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

    print(f"📦 Retrieved {len(chunks)} chunks from Qdrant in {retrieval_ms:.1f}ms")

    if rag_service.is_fallback_needed(chunks):
        fallback = rag_service.get_zero_hallucination_fallback()
        print(f"\n🛡️ Zero-Hallucination Guard Triggered:\n{fallback}\n")
        return {
            "query": query_text,
            "model": model_name,
            "answer": fallback,
            "citations": [],
            "retrieved_chunks": [],
            "is_grounded": False,
        }

    citations = rag_service.extract_citations(chunks)

    print("\n📚 Identified Transcript Citations:")
    for idx, c in enumerate(citations, 1):
        print(f"  [{idx}] {c.guest_name} in \"{c.episode_title}\" [{c.timestamp}] -> {c.youtube_url or 'N/A'}")

    print("\n" + "=" * 60)
    print("🤖 Lenny Growth Assistant Response:")
    print("=" * 60 + "\n")

    full_response = ""
    try:
        if stream:
            async for token in rag_service.astream_query(query=query_text, llm_client=llm, top_k=top_k):
                sys.stdout.write(token)
                sys.stdout.flush()
                full_response += token
            print("\n")
        else:
            result = await rag_service.query(query=query_text, llm_client=llm, top_k=top_k)
            full_response = result["answer"]
            print(full_response)
            print("\n")
    except OllamaUnavailableException as exc:
        print(f"\n❌ Ollama Connection Error: {exc.message}\n")
        return {"error": exc.message, "type": "OllamaUnavailableException"}
    except Exception as exc:
        print(f"\n❌ Generation Error: {exc}\n")
        return {"error": str(exc)}

    # Artifact extraction
    parsed = artifact_service.parse_artifacts(full_response)
    if parsed.has_artifact:
        print("\n🎨 Detected Artifacts:")
        for art in parsed.artifacts:
            print(f"  • [{art.artifact_type.value.upper()}] {art.title} ({len(art.content)} chars)")

    total_time = time.perf_counter() - start_time
    print(f"\n⏱️ Total latency: {total_time:.2f}s")

    return {
        "query": query_text,
        "model": model_name,
        "answer": full_response,
        "citations": [c.model_dump() for c in citations],
        "has_artifact": parsed.has_artifact,
        "artifacts_count": len(parsed.artifacts),
        "total_latency_seconds": round(total_time, 2),
    }


async def run_ship30_essay(
    topic: str,
    model_name: str,
    top_k: int = 5,
    stream: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Generate a dedicated Ship 30 for 30 essay grounded in Lenny transcripts."""
    cfg = settings or get_settings()
    rag_service = RAGService(settings=cfg)
    ship30_service = Ship30Service(rag_service=rag_service)

    print(f"\n✍️ Generating 'Ship 30 for 30' Essay on: '{topic}' (model: {model_name})...")
    start_time = time.perf_counter()

    try:
        llm = get_llm_client(model_name=model_name, settings=cfg)
    except Exception as exc:
        print(f"❌ Failed to initialize LLM client: {exc}")
        return {"error": str(exc)}

    print("\n" + "=" * 60)
    print("📝 Ship 30 for 30 Essay Output:")
    print("=" * 60 + "\n")

    full_essay = ""
    try:
        if stream:
            async for token in ship30_service.astream_essay(topic=topic, llm_client=llm, top_k=top_k):
                sys.stdout.write(token)
                sys.stdout.flush()
                full_essay += token
            print("\n")
            analysis = ship30_service.analyze_essay_structure(full_essay)
        else:
            result = await ship30_service.generate_essay(topic=topic, llm_client=llm, top_k=top_k)
            full_essay = result["essay"]
            analysis = result["analysis"]
            print(full_essay)
            print("\n")
    except OllamaUnavailableException as exc:
        print(f"\n❌ Ollama Connection Error: {exc.message}\n")
        return {"error": exc.message, "type": "OllamaUnavailableException"}
    except Exception as exc:
        print(f"\n❌ Essay Generation Error: {exc}\n")
        return {"error": str(exc)}

    total_time = time.perf_counter() - start_time
    print("=" * 60)
    print("📊 Ship 30 Structural Analysis:")
    print(f"  • Word Count: {analysis['word_count']} words")
    print(f"  • Headers: {analysis['header_count']}")
    print(f"  • Bolded Bullets: {analysis['bold_bullets_count']}")
    print(f"  • 3-Step Checklist: {'✅ Present' if analysis['has_action_checklist'] else '❌ Missing'}")
    print(f"  • Citations Detected: {'✅ Present' if analysis['has_guest_citations'] else '❌ Missing'}")
    print(f"  • Latency: {total_time:.2f}s")
    print("=" * 60 + "\n")

    return {
        "topic": topic,
        "model": model_name,
        "essay": full_essay,
        "analysis": analysis,
        "total_latency_seconds": round(total_time, 2),
    }


def main() -> None:
    """CLI entrypoint for interactive testing."""
    parser = argparse.ArgumentParser(description="Lenny Growth Assistant CLI & AI Service Tester")
    parser.add_argument("--query", "-q", type=str, help="RAG question to query")
    parser.add_argument("--ship30", action="store_true", help="Generate a Ship 30 for 30 essay")
    parser.add_argument("--topic", "-t", type=str, help="Topic for Ship 30 essay")
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=ModelName.CLAUDE_3_5_SONNET.value,
        help="Model to use (claude-3-5-sonnet, gpt-4o, llama3.2, mistral)",
    )
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of chunks to retrieve")
    parser.add_argument("--no-stream", action="store_true", help="Disable token streaming")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    if args.ship30:
        topic = args.topic or args.query or "How to transition from Product-Led Growth to Sales-Led Enterprise"
        res = asyncio.run(
            run_ship30_essay(
                topic=topic,
                model_name=args.model,
                top_k=args.top_k,
                stream=not args.no_stream and args.format == "text",
            )
        )
        if args.format == "json":
            print(json.dumps(res, indent=2))
    elif args.query:
        res = asyncio.run(
            run_rag_query(
                query_text=args.query,
                model_name=args.model,
                top_k=args.top_k,
                stream=not args.no_stream and args.format == "text",
            )
        )
        if args.format == "json":
            print(json.dumps(res, indent=2))
    else:
        # Default demo query
        print("💡 No query specified. Running default demo query on PLG Strategy...\n")
        res = asyncio.run(
            run_rag_query(
                query_text="What are Elena Verna's key principles for Product-Led Growth?",
                model_name=args.model,
                top_k=args.top_k,
                stream=not args.no_stream,
            )
        )


if __name__ == "__main__":
    main()
