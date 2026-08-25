"""CLI script for ingesting podcast transcripts into Qdrant hybrid vector collection.

Usage:
    uv run python -m app.scripts.ingest
    uv run python -m app.scripts.ingest --recreate
    uv run python -m app.scripts.ingest --transcripts-dir ../data/transcripts
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from qdrant_client import QdrantClient
from app.core.config import Settings, get_settings
from app.scripts.chunker import find_default_transcripts_dir
from app.services.chunker import TranscriptChunker
from app.services.vector_store import HybridVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("ingest_cli")


def get_resilient_qdrant_client(
    settings: Settings,
    explicit_url: str | None = None,
    explicit_path: str | None = None,
) -> tuple[QdrantClient, str]:
    """Connect to remote Qdrant if reachable, or gracefully fall back to local disk storage."""
    target_url = explicit_url or settings.QDRANT_URL
    target_path = explicit_path or settings.QDRANT_STORAGE_PATH

    # If explicit path or storage path configured, use local storage
    if target_path:
        storage_dir = Path(target_path).resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local embedded Qdrant storage at: {storage_dir}")
        return QdrantClient(path=str(storage_dir)), f"Local Embedded ({storage_dir})"

    # Try connecting to remote Qdrant
    try:
        client = QdrantClient(
            url=target_url,
            api_key=settings.QDRANT_API_KEY,
            timeout=2.0,
            check_compatibility=False,
        )
        # Test connection
        client.get_collections()
        logger.info(f"Connected to Qdrant instance at: {target_url}")
        return client, f"Remote ({target_url})"
    except Exception as exc:
        logger.warning(
            f"Could not connect to Qdrant server at '{target_url}' ({exc}). "
            "Falling back to local disk storage in 'data/qdrant_storage' for offline persistence."
        )
        default_local_dir = Path("data/qdrant_storage").resolve()
        default_local_dir.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(default_local_dir)), f"Local Embedded Fallback ({default_local_dir})"


def run_ingestion(
    transcripts_dir: Path | str | None = None,
    recreate: bool = True,
    batch_size: int = 32,
    qdrant_url: str | None = None,
    storage_path: str | None = None,
    min_tokens: int = 500,
    max_tokens: int = 700,
    overlap_tokens: int = 100,
    close_client: bool = True,
) -> dict:
    """Execute the full chunking and hybrid vector ingestion pipeline."""
    if batch_size < 1:
        raise ValueError(f"batch_size must be at least 1, got {batch_size}")

    start_time = time.time()
    settings = get_settings()


    # 1. Resolve transcripts directory using settings
    input_path = Path(transcripts_dir) if transcripts_dir else find_default_transcripts_dir(settings)
    if not input_path.exists():
        logger.error(f"Transcripts corpus directory not found at: {input_path}")
        raise FileNotFoundError(f"Transcripts corpus directory not found at: {input_path}")

    logger.info(f"1. Scanning transcripts corpus from: {input_path}")
    chunker = TranscriptChunker(
        min_tokens=min_tokens,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )
    chunks = chunker.chunk_directory(input_path, strict=True)
    if not chunks:
        logger.error("No transcript chunks could be generated.")
        raise ValueError("No transcript chunks could be generated.")

    logger.info(f"Generated {len(chunks)} semantic chunks across corpus.")

    # 2. Connect to Qdrant
    logger.info("2. Initializing Qdrant connection and vector store...")
    client, conn_desc = get_resilient_qdrant_client(settings, explicit_url=qdrant_url, explicit_path=storage_path)

    try:
        vector_store = HybridVectorStore(settings=settings, client=client)

        # 3. Prepare collection
        logger.info(f"3. Setting up collection '{settings.QDRANT_COLLECTION_NAME}' (recreate={recreate})...")
        vector_store.ensure_collection(recreate=recreate)

        # 4. Upsert chunks
        logger.info(f"4. Indexing hybrid dense + sparse vectors (batch size: {batch_size})...")
        upserted = vector_store.upsert_chunks(chunks=chunks, batch_size=batch_size)

        # 5. Fetch stats
        stats = vector_store.get_collection_stats()
        duration = time.time() - start_time

        # 6. Pretty print report
        print("\n" + "=" * 65)
        print("🚀  LENNY GROWTH ASSISTANT — HYBRID INGESTION MILESTONE")
        print("=" * 65)
        print("Status              : SUCCESS")
        print(f"Target Collection   : {stats.get('collection_name')}")
        print(f"Qdrant Backend      : {conn_desc}")
        print(f"Total Points Count  : {stats.get('points_count')} points")
        print(f"Dense Model         : {stats.get('dense_model')} (dim: {stats.get('dense_dim')})")
        print(f"Sparse Model        : {stats.get('sparse_model')}")
        print(f"Total Chunks Indexed: {upserted}")
        print(f"Duration            : {duration:.2f} seconds")
        print("-" * 65)
        print("Indexed Guest Episodes:")
        guest_counts: dict[str, int] = {}
        for c in chunks:
            guest_counts[c.guest_name] = guest_counts.get(c.guest_name, 0) + 1
        for guest, count in sorted(guest_counts.items()):
            print(f"  • {guest:<25} [{count} chunks]")
        print("=" * 65 + "\n")

        return {
            "status": "success",
            "points_count": stats.get("points_count"),
            "collection_name": stats.get("collection_name"),
            "chunks_indexed": upserted,
            "duration_seconds": duration,
        }
    finally:
        if close_client and client is not None:
            try:
                client.close()
            except Exception as exc:
                logger.debug(f"Error closing QdrantClient: {exc}")


def main() -> None:
    """CLI entry point for ingest."""
    parser = argparse.ArgumentParser(
        description="Index Lenny transcript corpus into Qdrant hybrid dense + sparse vector database."
    )
    parser.add_argument(
        "--transcripts-dir",
        "-t",
        type=str,
        default=None,
        help="Path to directory containing transcript files (default: ../data/transcripts)",
    )
    parser.add_argument(
        "--recreate",
        "-r",
        action="store_true",
        default=True,
        help="Recreate the Qdrant collection from scratch (default: True)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=32,
        help="Batch size for generating embeddings and upserting points (default: 32)",
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default=None,
        help="Custom Qdrant URL (overrides QDRANT_URL setting)",
    )
    parser.add_argument(
        "--storage-path",
        type=str,
        default=None,
        help="Custom local disk path for embedded Qdrant storage",
    )

    args = parser.parse_args()
    if args.batch_size < 1:
        logger.error(f"--batch-size must be at least 1, got {args.batch_size}")
        sys.exit(1)

    try:
        run_ingestion(

            transcripts_dir=args.transcripts_dir,
            recreate=args.recreate,
            batch_size=args.batch_size,
            qdrant_url=args.qdrant_url,
            storage_path=args.storage_path,
        )
    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
