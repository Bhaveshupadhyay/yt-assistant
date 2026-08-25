import logging
import time
from typing import Any
from qdrant_client import QdrantClient, models
from app.core.clients import (
    get_dense_embedding_model,
    get_qdrant_sync_client,
    get_sparse_embedding_model,
)
from app.core.config import Settings, get_settings
from app.schemas.chunk import TranscriptChunk

logger = logging.getLogger(__name__)


class HybridVectorStore:
    """Synchronous Qdrant hybrid vector store client supporting Dense and BM25 Sparse vectors."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: QdrantClient | None = None,
        dense_model: Any | None = None,
        sparse_model: Any | None = None,
    ) -> None:
        """Initialize the hybrid vector store."""
        self.settings = settings or get_settings()
        self.collection_name = self.settings.QDRANT_COLLECTION_NAME
        self.client: QdrantClient = client or get_qdrant_sync_client(self.settings)
        if dense_model is not None:
            self.dense_model = dense_model
        else:
            self.dense_model = get_dense_embedding_model(self.settings.EMBEDDING_DENSE_MODEL)

        try:
            probe = list(self.dense_model.embed(["probe"]))[0]
            self.dense_dim = len(probe)
        except Exception:
            self.dense_dim = self.settings.EMBEDDING_DENSE_DIMENSION

        self.sparse_model = sparse_model or get_sparse_embedding_model(self.settings.EMBEDDING_SPARSE_MODEL)



    def ensure_collection(
        self,
        collection_name: str | None = None,
        recreate: bool = False,
    ) -> None:
        """Create or recreate the Qdrant hybrid vector collection with Dense and Sparse configurations."""
        target_col = collection_name or self.collection_name
        logger.info(f"Ensuring Qdrant collection '{target_col}' (recreate={recreate})...")

        vectors_config = {
            "dense": models.VectorParams(
                size=self.dense_dim,
                distance=models.Distance.COSINE,
            )
        }
        sparse_vectors_config = {
            "sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False),
            )
        }

        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == target_col for c in collections)
        except Exception as exc:
            logger.warning(f"Error checking existing collections: {exc}. Attempting create.")
            exists = False

        if exists:
            if recreate:
                logger.info(f"Recreating collection '{target_col}'...")
                self.client.delete_collection(collection_name=target_col)
                self.client.create_collection(
                    collection_name=target_col,
                    vectors_config=vectors_config,
                    sparse_vectors_config=sparse_vectors_config,
                )
                logger.info(f"Collection '{target_col}' successfully recreated.")
            else:
                logger.info(f"Collection '{target_col}' already exists.")
        else:
            logger.info(f"Creating new hybrid collection '{target_col}'...")
            self.client.create_collection(
                collection_name=target_col,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
            logger.info(f"Collection '{target_col}' created.")

    def upsert_chunks(
        self,
        chunks: list[TranscriptChunk],
        collection_name: str | None = None,
        batch_size: int = 32,
    ) -> int:
        """Embed and upsert transcript chunks in batches into Qdrant."""
        if not chunks:
            logger.warning("No chunks provided for upsert.")
            return 0

        target_col = collection_name or self.collection_name
        self.ensure_collection(collection_name=target_col, recreate=False)

        total = len(chunks)
        upserted_count = 0
        logger.info(f"Starting bulk hybrid embedding and upsert of {total} chunks into '{target_col}'...")

        for i in range(0, total, batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]

            # Generate dense embeddings
            dense_vectors = list(self.dense_model.embed(texts))

            # Generate sparse BM25 / SPLADE embeddings
            sparse_vectors = list(self.sparse_model.embed(texts))

            if len(dense_vectors) != len(batch) or len(sparse_vectors) != len(batch):
                raise ValueError(
                    f"Embedding batch size mismatch: expected {len(batch)} embeddings, "
                    f"got {len(dense_vectors)} dense and {len(sparse_vectors)} sparse embeddings."
                )

            points: list[models.PointStruct] = []
            for chunk, dense_vec, sparse_vec in zip(batch, dense_vectors, sparse_vectors, strict=True):

                # Ensure dense vector is a list of floats
                dense_list = dense_vec.tolist() if hasattr(dense_vec, "tolist") else list(dense_vec)

                # Format sparse vector
                sparse_struct = models.SparseVector(
                    indices=sparse_vec.indices.tolist() if hasattr(sparse_vec.indices, "tolist") else list(sparse_vec.indices),
                    values=sparse_vec.values.tolist() if hasattr(sparse_vec.values, "tolist") else list(sparse_vec.values),
                )

                payload = {
                    "chunk_id": chunk.chunk_id,
                    "episode_id": chunk.episode_id,
                    "episode_title": chunk.episode_title,
                    "guest_name": chunk.guest_name,
                    "guest_role": chunk.guest_role,
                    "topic": chunk.topic,
                    "url": chunk.url,
                    "timestamp": chunk.timestamp,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    "citation_label": chunk.citation_label,
                }

                points.append(
                    models.PointStruct(
                        id=chunk.chunk_id,
                        vector={
                            "dense": dense_list,
                            "sparse": sparse_struct,
                        },
                        payload=payload,
                    )
                )

            # Robust upsert with retry for remote Qdrant Cloud uploads
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    self.client.upsert(collection_name=target_col, points=points)
                    break
                except Exception as exc:
                    if attempt == max_retries:
                        logger.error(f"Failed to upsert batch {i // batch_size + 1} after {max_retries} attempts: {exc}")
                        raise
                    logger.warning(f"Upsert attempt {attempt} failed ({exc}). Retrying in {attempt * 2}s...")
                    time.sleep(attempt * 2)

            upserted_count += len(points)
            if (i // batch_size + 1) % 10 == 0 or upserted_count == total:
                logger.info(f"Upserted batch {i // batch_size + 1} ({upserted_count}/{total} chunks)...")

        logger.info(f"Finished upserting {upserted_count} chunks to '{target_col}'.")
        return upserted_count

    def get_collection_stats(self, collection_name: str | None = None) -> dict[str, Any]:
        """Retrieve point count and status for the collection."""
        target_col = collection_name or self.collection_name
        try:
            info = self.client.get_collection(collection_name=target_col)
            count = self.client.count(collection_name=target_col).count
            return {
                "collection_name": target_col,
                "points_count": count,
                "status": getattr(info, "status", "green"),
                "vectors_count": getattr(info, "vectors_count", count),
                "dense_dim": self.dense_dim,
                "dense_model": self.settings.EMBEDDING_DENSE_MODEL,
                "sparse_model": self.settings.EMBEDDING_SPARSE_MODEL,
            }
        except Exception as exc:
            logger.error(f"Failed to get collection stats for '{target_col}': {exc}")
            return {
                "collection_name": target_col,
                "points_count": 0,
                "error": str(exc),
            }

    def search(
        self,
        query: str,
        limit: int = 5,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search over dense and sparse vectors with reciprocal rank fusion (RRF)."""
        target_col = collection_name or self.collection_name
        query_dense = list(self.dense_model.embed([query]))[0]
        query_sparse = list(self.sparse_model.embed([query]))[0]

        dense_list = query_dense.tolist() if hasattr(query_dense, "tolist") else list(query_dense)
        sparse_struct = models.SparseVector(
            indices=query_sparse.indices.tolist() if hasattr(query_sparse.indices, "tolist") else list(query_sparse.indices),
            values=query_sparse.values.tolist() if hasattr(query_sparse.values, "tolist") else list(query_sparse.values),
        )

        # Hybrid query using Qdrant prefetch & RRF fusion
        results = self.client.query_points(
            collection_name=target_col,
            prefetch=[
                models.Prefetch(
                    query=dense_list,
                    using="dense",
                    limit=limit * 2,
                ),
                models.Prefetch(
                    query=sparse_struct,
                    using="sparse",
                    limit=limit * 2,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
        )

        formatted: list[dict[str, Any]] = []
        for p in results.points:
            formatted.append({
                "id": p.id,
                "score": p.score,
                "payload": p.payload,
            })
        return formatted
