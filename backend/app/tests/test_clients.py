"""Tests for centralized client pool and lifecycle management."""

import httpx
import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from app.core.clients import (
    close_all_clients,
    get_anthropic_client,
    get_async_engine,
    get_ollama_client,
    get_openai_client,
    get_qdrant_client,
    get_session_factory,
    init_all_clients,
)
from app.core.config import Settings
from app.utils.clients import get_async_engine as utils_get_async_engine


def test_get_database_engine_and_factory():
    """Verify database async engine and session factory getters."""
    settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:")
    engine = get_async_engine(settings)
    assert isinstance(engine, AsyncEngine)

    factory = get_session_factory(settings)
    assert isinstance(factory, async_sessionmaker)


def test_qdrant_client_creation():
    """Verify AsyncQdrantClient instantiation via get_qdrant_client."""
    settings = Settings(QDRANT_URL="http://localhost:6333")
    client = get_qdrant_client(settings)
    assert isinstance(client, AsyncQdrantClient)


def test_http_clients_creation():
    """Verify Ollama, Anthropic, and OpenAI HTTP clients."""
    settings = Settings(
        OLLAMA_BASE_URL="http://localhost:11434",
        ANTHROPIC_API_KEY="test-anthropic-key",
        OPENAI_API_KEY="test-openai-key",
    )

    ollama = get_ollama_client(settings)
    assert isinstance(ollama, httpx.AsyncClient)
    assert str(ollama.base_url).rstrip("/") == "http://localhost:11434"

    anthropic = get_anthropic_client(settings)
    assert isinstance(anthropic, httpx.AsyncClient)
    assert anthropic.headers.get("x-api-key") == "test-anthropic-key"

    openai = get_openai_client(settings)
    assert isinstance(openai, httpx.AsyncClient)
    assert openai.headers.get("authorization") == "Bearer test-openai-key"


def test_utils_clients_proxy():
    """Verify app.utils.clients correctly re-exports core.clients functions."""
    engine = utils_get_async_engine()
    assert isinstance(engine, AsyncEngine)


@pytest.mark.asyncio
async def test_init_and_close_all_clients():
    """Verify full client pool startup initialization and graceful shutdown."""
    settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:")
    await init_all_clients(settings)
    await close_all_clients()
