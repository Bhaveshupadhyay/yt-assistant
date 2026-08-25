"""Clients module proxy (re-exports from app.core.clients for convenience)."""

from app.core.clients import (
    close_all_clients,
    close_cloud_llm_clients,
    close_database_engine,
    close_ollama_client,
    close_qdrant_client,
    get_anthropic_client,
    get_async_engine,
    get_embedding_model,
    get_ollama_client,
    get_openai_client,
    get_qdrant_client,
    get_session_factory,
    init_all_clients,
)

__all__ = [
    "get_async_engine",
    "get_session_factory",
    "close_database_engine",
    "get_qdrant_client",
    "close_qdrant_client",
    "get_embedding_model",
    "get_ollama_client",
    "close_ollama_client",
    "get_anthropic_client",
    "get_openai_client",
    "close_cloud_llm_clients",
    "init_all_clients",
    "close_all_clients",
]
