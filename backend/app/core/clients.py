"""Centralized external service clients and connection pool management.

Follows the singleton connection pooling pattern for:
- PostgreSQL / SQLite (Reuses SQLAlchemy 2.0 Async Engine & Sessionmaker from database module)
- Qdrant Vector Database (AsyncQdrantClient)
- FastEmbed (Text Embedding Model Engine)
- Ollama Local Daemon (HTTPX Async Client with pooling and keep-alive)
- Anthropic Claude & OpenAI API (HTTPX Async Clients with connection pooling)
"""

import logging
from typing import Any
import httpx
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from app.core.config import Settings, get_settings
from app.core.database import (
    close_db,
    create_engine_and_session_factory,
    engine as _db_engine,
    async_session_factory as _db_session_factory,
)

logger = logging.getLogger(__name__)

# Global client / pool singletons
_qdrant_client: AsyncQdrantClient | None = None
_qdrant_sync_client: Any | None = None
_ollama_client: httpx.AsyncClient | None = None
_anthropic_client: httpx.AsyncClient | None = None
_openai_client: httpx.AsyncClient | None = None
_dense_embedding_models: dict[str, Any] = {}
_sparse_embedding_models: dict[str, Any] = {}


# ==========================================
# 1. Database (PostgreSQL / SQLite) Engine & Factory
# ==========================================
def get_async_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the shared SQLAlchemy 2.0 AsyncEngine singleton from the database module."""
    if settings is not None:
        custom_engine, _ = create_engine_and_session_factory(settings)
        return custom_engine
    return _db_engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Return the shared async sessionmaker factory from the database module."""
    if settings is not None:
        _, custom_factory = create_engine_and_session_factory(settings)
        return custom_factory
    return _db_session_factory


async def close_database_engine() -> None:
    """Dispose of the database engine connection pool."""
    logger.info("Closing database engine connection pool...")
    await close_db(_db_engine)
    logger.info("Database engine closed.")


# ==========================================
# 2. Qdrant Vector Database Clients (Async & Sync)
# ==========================================
def _resolve_effective_qdrant_path(cfg: Settings) -> str | None:
    """Check if an explicit or default local Qdrant storage path exists on disk."""
    if cfg.QDRANT_STORAGE_PATH:
        return cfg.QDRANT_STORAGE_PATH
    import os
    from pathlib import Path
    for candidate in ["data/qdrant_storage", "../data/qdrant_storage", "backend/data/qdrant_storage"]:
        if os.path.exists(candidate) and os.path.isdir(candidate):
            return str(Path(candidate).resolve())
    return None


def get_qdrant_client(settings: Settings | None = None) -> AsyncQdrantClient:
    """Return or lazily create the asynchronous Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        cfg = settings or get_settings()
        local_path = _resolve_effective_qdrant_path(cfg)
        if local_path and not cfg.QDRANT_API_KEY:
            logger.info(f"Initializing AsyncQdrantClient with local storage path: {local_path}")
            _qdrant_client = AsyncQdrantClient(path=local_path)
        else:
            logger.info(f"Initializing AsyncQdrantClient for URL: {cfg.QDRANT_URL}")
            _qdrant_client = AsyncQdrantClient(
                url=cfg.QDRANT_URL,
                api_key=cfg.QDRANT_API_KEY,
                timeout=10.0,
                check_compatibility=False,
            )
    return _qdrant_client


def get_qdrant_sync_client(settings: Settings | None = None) -> Any:
    """Return or lazily create the synchronous Qdrant client for data ingestion and scripts."""
    global _qdrant_sync_client
    if _qdrant_sync_client is None:
        from qdrant_client import QdrantClient

        cfg = settings or get_settings()
        local_path = _resolve_effective_qdrant_path(cfg)
        if local_path and not cfg.QDRANT_API_KEY:
            logger.info(f"Initializing QdrantClient with local storage path: {local_path}")
            _qdrant_sync_client = QdrantClient(path=local_path)
        else:
            logger.info(f"Initializing QdrantClient for URL: {cfg.QDRANT_URL}")
            _qdrant_sync_client = QdrantClient(
                url=cfg.QDRANT_URL,
                api_key=cfg.QDRANT_API_KEY,
                timeout=10.0,
                check_compatibility=False,
            )
    return _qdrant_sync_client


async def close_qdrant_client() -> None:
    """Close Qdrant client connections."""
    global _qdrant_client, _qdrant_sync_client
    if _qdrant_client is not None:
        logger.info("Closing AsyncQdrantClient connection...")
        try:
            await _qdrant_client.close()
        finally:
            _qdrant_client = None
    if _qdrant_sync_client is not None:
        try:
            _qdrant_sync_client.close()
        finally:
            _qdrant_sync_client = None


# ==========================================
# 3. FastEmbed Embedding Model Clients (Dense & Sparse)
# ==========================================
def get_dense_embedding_model(
    model_name: str | None = None,
) -> Any:
    """Return or lazily initialize the FastEmbed Dense TextEmbedding model cached by name."""
    global _dense_embedding_models
    target_model = model_name or get_settings().EMBEDDING_DENSE_MODEL
    if target_model not in _dense_embedding_models:
        from fastembed import TextEmbedding

        logger.info(f"Initializing FastEmbed Dense model: {target_model}")
        _dense_embedding_models[target_model] = TextEmbedding(model_name=target_model)
    return _dense_embedding_models[target_model]


def get_sparse_embedding_model(
    model_name: str | None = None,
) -> Any:
    """Return or lazily initialize the FastEmbed SparseTextEmbedding model cached by name."""
    global _sparse_embedding_models
    target_model = model_name or get_settings().EMBEDDING_SPARSE_MODEL
    if target_model not in _sparse_embedding_models:
        from fastembed import SparseTextEmbedding

        logger.info(f"Initializing FastEmbed Sparse model: {target_model}")
        _sparse_embedding_models[target_model] = SparseTextEmbedding(model_name=target_model)
    return _sparse_embedding_models[target_model]



def get_embedding_model(
    model_name: str | None = None,
) -> Any:
    """Backwards-compatible alias for the default dense embedding model."""
    return get_dense_embedding_model(model_name=model_name)



# ==========================================
# 4. Ollama Local Daemon Client
# ==========================================
def get_ollama_client(settings: Settings | None = None) -> httpx.AsyncClient:
    """Return or lazily create the HTTPX AsyncClient for Ollama local daemon."""
    global _ollama_client
    if _ollama_client is None or _ollama_client.is_closed:
        cfg = settings or get_settings()
        logger.info(f"Initializing Ollama AsyncClient (base_url={cfg.OLLAMA_BASE_URL})...")
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        _ollama_client = httpx.AsyncClient(
            base_url=cfg.OLLAMA_BASE_URL,
            timeout=httpx.Timeout(connect=2.0, read=120.0, write=10.0, pool=5.0),
            limits=limits,
        )
    return _ollama_client


async def close_ollama_client() -> None:
    """Close Ollama AsyncClient."""
    global _ollama_client
    if _ollama_client is not None:
        logger.info("Closing Ollama AsyncClient...")
        try:
            if not _ollama_client.is_closed:
                await _ollama_client.aclose()
        finally:
            _ollama_client = None


# ==========================================
# 5. Cloud LLM Clients (Anthropic & OpenAI)
# ==========================================
def get_anthropic_client(settings: Settings | None = None) -> httpx.AsyncClient:
    """Return or lazily create the HTTPX AsyncClient for Anthropic API."""
    global _anthropic_client
    if _anthropic_client is None or _anthropic_client.is_closed:
        cfg = settings or get_settings()
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if cfg.ANTHROPIC_API_KEY:
            headers["x-api-key"] = cfg.ANTHROPIC_API_KEY

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=30)
        _anthropic_client = httpx.AsyncClient(
            base_url="https://api.anthropic.com/v1",
            headers=headers,
            timeout=httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=5.0),
            limits=limits,
        )
    return _anthropic_client


def get_openai_client(settings: Settings | None = None) -> httpx.AsyncClient:
    """Return or lazily create the HTTPX AsyncClient for OpenAI API."""
    global _openai_client
    if _openai_client is None or _openai_client.is_closed:
        cfg = settings or get_settings()
        headers = {
            "content-type": "application/json",
        }
        if cfg.OPENAI_API_KEY:
            headers["authorization"] = f"Bearer {cfg.OPENAI_API_KEY}"

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=30)
        _openai_client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers=headers,
            timeout=httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=5.0),
            limits=limits,
        )
    return _openai_client


async def close_cloud_llm_clients() -> None:
    """Close Anthropic and OpenAI HTTP clients."""
    global _anthropic_client, _openai_client
    if _anthropic_client is not None:
        try:
            if not _anthropic_client.is_closed:
                await _anthropic_client.aclose()
        finally:
            _anthropic_client = None
    if _openai_client is not None:
        try:
            if not _openai_client.is_closed:
                await _openai_client.aclose()
        finally:
            _openai_client = None


# ==========================================
# 6. Global Lifecycle Management (Startup / Shutdown)
# ==========================================
async def init_all_clients(settings: Settings | None = None, create_tables: bool = True) -> None:
    """Eagerly initialize all client singletons and database schema on startup."""
    cfg = settings or get_settings()
    logger.info(f"Initializing all infrastructure clients for {cfg.APP_NAME}...")

    # 1. Initialize Database Engine & Tables
    engine_inst = get_async_engine(cfg)
    get_session_factory(cfg)

    if create_tables:
        from app.core.database import init_db

        logger.info("Verifying and auto-creating database tables...")
        await init_db(engine_inst)

    # 2. Warm up Qdrant, Ollama and Cloud Clients
    get_qdrant_client(cfg)
    ollama = get_ollama_client(cfg)
    try:
        resp = await ollama.get("/api/tags", timeout=0.5)
        if resp.status_code == 200:
            logger.info("Ollama local daemon detected and reachable.")
    except Exception:
        logger.warning(
            f"Ollama local daemon is currently offline or unreachable at {cfg.OLLAMA_BASE_URL} "
            "(cloud models and sessions remain fully functional; local models will be degraded)."
        )

    logger.info("All infrastructure clients and connection pools initialized.")


async def close_all_clients() -> None:
    """Gracefully close all global client pools and connections on application shutdown."""
    logger.info("Closing all infrastructure client pools...")
    cleanup_routines = [
        ("database_engine", close_database_engine),
        ("qdrant_client", close_qdrant_client),
        ("ollama_client", close_ollama_client),
        ("cloud_llm_clients", close_cloud_llm_clients),
    ]

    for name, cleanup_fn in cleanup_routines:
        try:
            await cleanup_fn()
        except Exception as exc:
            logger.warning(f"Error while closing {name}: {exc}")

    logger.info("All infrastructure client pools closed.")
