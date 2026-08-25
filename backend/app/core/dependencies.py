"""Dependency injection providers for FastAPI routes."""

from collections.abc import AsyncGenerator
import logging
from typing import Any, Protocol, runtime_checkable
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings, get_settings
from app.core.database import async_session_factory
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMServiceProtocol(Protocol):
    """Protocol interface for LLM operations."""

    async def astream_chat(self, messages: list[dict[str, str]], system_prompt: str) -> Any: ...


@runtime_checkable
class RAGServiceProtocol(Protocol):
    """Protocol interface for RAG operations."""

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]: ...


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an AsyncSession per request with transaction control."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_session_repository(
    db: AsyncSession = Depends(get_db),
) -> SessionRepository:
    """Dependency provider for SessionRepository."""
    return SessionRepository(session=db)


def get_message_repository(
    db: AsyncSession = Depends(get_db),
) -> MessageRepository:
    """Dependency provider for MessageRepository."""
    return MessageRepository(session=db)


def get_artifact_repository(
    db: AsyncSession = Depends(get_db),
) -> ArtifactRepository:
    """Dependency provider for ArtifactRepository."""
    return ArtifactRepository(session=db)


class DefaultStubLLMService:
    """Placeholder service provider until Phase 2/3 LLM services are connected."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def astream_chat(self, messages: list[dict[str, str]], system_prompt: str) -> Any:
        raise NotImplementedError("LLMService will be fully implemented in Phase 2.")


class DefaultStubRAGService:
    """Placeholder RAG service provider until Phase 2/3 RAG pipeline is connected."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError("RAGService will be fully implemented in Phase 2.")


def get_llm_service(
    settings: Settings = Depends(get_settings),
) -> LLMServiceProtocol:
    """Dependency provider for LLM service."""
    return DefaultStubLLMService(settings=settings)


def get_rag_service(
    settings: Settings = Depends(get_settings),
) -> RAGServiceProtocol:
    """Dependency provider for RAG service."""
    return DefaultStubRAGService(settings=settings)
