"""Integration tests for hybrid vector store and ingestion pipeline."""

from pathlib import Path
from typing import Any
import pytest
from qdrant_client import QdrantClient
from app.core.config import Settings
from app.schemas.chunk import TranscriptChunk
from app.scripts.ingest import get_resilient_qdrant_client, run_ingestion
from app.services.vector_store import HybridVectorStore


@pytest.fixture
def mock_qdrant_client(tmp_path: Path) -> QdrantClient:
    """Provide an in-memory or embedded disk QdrantClient for testing."""
    return QdrantClient(path=str(tmp_path / "qdrant_test_db"))


@pytest.fixture
def sample_chunks() -> list[TranscriptChunk]:
    """Provide test sample transcript chunks."""
    return [
        TranscriptChunk(
            chunk_id="550e8400-e29b-41d4-a716-446655440000",
            episode_id="elena_verna_plg",
            episode_title="Elena Verna on B2B Growth",
            guest_name="Elena Verna",
            guest_role="Growth Advisor",
            topic="B2B Growth & PLG",
            url="https://example.com/elena",
            timestamp="00:00:15 - 00:05:00",
            chunk_index=0,
            total_chunks=1,
            text="[Elena Verna | Elena Verna on B2B Growth | 00:00:15]\n\nElena: Product-Led Growth is a distribution mechanism where the product acquires, activates, and retains users.",
            token_count=150,
        ),
        TranscriptChunk(
            chunk_id="550e8400-e29b-41d4-a716-446655440001",
            episode_id="shreyas_doshi_pm",
            episode_title="Shreyas Doshi on Product",
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


def test_run_ingestion_invalid_batch_size() -> None:
    """Test run_ingestion rejects non-positive batch sizes."""
    with pytest.raises(ValueError, match="batch_size"):
        run_ingestion(batch_size=0)
    with pytest.raises(ValueError, match="batch_size"):
        run_ingestion(batch_size=-5)


def test_upsert_mismatched_embeddings_raises(mock_qdrant_client: QdrantClient, sample_chunks: list[TranscriptChunk]) -> None:
    """Test upsert_chunks raises ValueError if embedding models return fewer vectors than input batch."""
    class BadDenseModel:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 768]  # Only 1 embedding for a batch of 2!

    store = HybridVectorStore(client=mock_qdrant_client, dense_model=BadDenseModel())
    with pytest.raises(ValueError, match="Embedding batch size mismatch"):
        store.upsert_chunks(sample_chunks, batch_size=2)
