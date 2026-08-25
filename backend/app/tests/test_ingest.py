"""Tests for HybridVectorStore and transcript ingestion pipeline."""

from pathlib import Path
import pytest
from qdrant_client import QdrantClient
from app.core.config import Settings
from app.schemas.chunk import TranscriptChunk
from app.scripts.ingest import get_resilient_qdrant_client, run_ingestion
from app.services.vector_store import HybridVectorStore


@pytest.fixture
def mock_qdrant_client() -> QdrantClient:
    """Provide an isolated in-memory Qdrant client for testing."""
    return QdrantClient(":memory:")


@pytest.fixture
def sample_chunks() -> list[TranscriptChunk]:
    """Provide sample TranscriptChunks for vector indexing tests."""
    return [
        TranscriptChunk(
            chunk_id="c1a2b3c4-0000-0000-0000-000000000001",
            episode_id="ep_elena",
            episode_title="Elena Verna on B2B Growth and PLG",
            guest_name="Elena Verna",
            guest_role="Head of Growth",
            topic="B2B Growth, PLG",
            url="https://example.com/elena",
            timestamp="00:02:00 - 00:05:00",
            chunk_index=0,
            total_chunks=1,
            text="[Elena Verna | PLG Loops | 00:02:00]\n\nProduct-Led Growth is a distribution model where user activation drives expansion.",
            token_count=120,
        ),
        TranscriptChunk(
            chunk_id="c1a2b3c4-0000-0000-0000-000000000002",
            episode_id="ep_shreyas",
            episode_title="Shreyas Doshi on High Agency and LNO",
            guest_name="Shreyas Doshi",
            guest_role="Product Leader",
            topic="Product Management",
            url="https://example.com/shreyas",
            timestamp="00:03:00 - 00:07:00",
            chunk_index=0,
            total_chunks=1,
            text="[Shreyas Doshi | LNO Framework | 00:03:00]\n\nThe LNO framework categorizes tasks into Leverage, Neutral, and Overhead.",
            token_count=140,
        ),
    ]


def test_hybrid_vector_store_ensure_and_upsert(mock_qdrant_client: QdrantClient, sample_chunks: list[TranscriptChunk]) -> None:
    """Test creating a hybrid collection and upserting dense and sparse vectors."""
    store = HybridVectorStore(client=mock_qdrant_client)

    # 1. Ensure collection exists
    store.ensure_collection(collection_name="test_lenny", recreate=True)
    stats_before = store.get_collection_stats(collection_name="test_lenny")
    assert stats_before["points_count"] == 0

    # 2. Upsert chunks
    upserted = store.upsert_chunks(chunks=sample_chunks, collection_name="test_lenny", batch_size=2)
    assert upserted == 2

    # 3. Check stats after upsert
    stats_after = store.get_collection_stats(collection_name="test_lenny")
    assert stats_after["points_count"] == 2
    assert stats_after["dense_dim"] == 768



def test_hybrid_search_retrieval(mock_qdrant_client: QdrantClient, sample_chunks: list[TranscriptChunk]) -> None:
    """Test hybrid search with Reciprocal Rank Fusion returns top relevant chunks."""
    store = HybridVectorStore(client=mock_qdrant_client)
    store.ensure_collection(collection_name="test_lenny", recreate=True)
    store.upsert_chunks(chunks=sample_chunks, collection_name="test_lenny")

    # Search for LNO framework
    results = store.search("LNO framework leverage neutral overhead", limit=2, collection_name="test_lenny")
    assert len(results) >= 1
    top_payload = results[0]["payload"]
    assert top_payload["guest_name"] == "Shreyas Doshi"
    assert "LNO" in top_payload["text"]

    # Search for PLG
    plg_results = store.search("product-led growth distribution activation", limit=2, collection_name="test_lenny")
    assert len(plg_results) >= 1
    plg_payload = plg_results[0]["payload"]
    assert plg_payload["guest_name"] == "Elena Verna"


def test_get_resilient_qdrant_client_fallback(tmp_path: Path) -> None:
    """Test that get_resilient_qdrant_client falls back to local storage when remote server is offline."""
    custom_settings = Settings(
        QDRANT_URL="http://localhost:59999",  # Unused port
        QDRANT_STORAGE_PATH=str(tmp_path / "offline_qdrant"),
    )
    client, desc = get_resilient_qdrant_client(custom_settings)
    assert isinstance(client, QdrantClient)
    assert "Local Embedded" in desc


def test_run_ingestion_pipeline_end_to_end(tmp_path: Path) -> None:
    """Test running the full ingestion pipeline from start to finish."""
    storage_dir = tmp_path / "test_ingest_storage"
    result = run_ingestion(
        recreate=True,
        batch_size=16,
        storage_path=str(storage_dir),
    )

    assert result["status"] == "success"
    assert result["points_count"] >= 12
    assert result["chunks_indexed"] >= 12
    assert result["duration_seconds"] > 0
