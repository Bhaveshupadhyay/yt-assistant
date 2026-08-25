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
from app.services.artifact_service import ArtifactService
from app.services.chat_service import ChatService
from app.services.health_service import HealthService
from app.services.llm.base import BaseLLMClient
from app.services.llm.factory import get_llm_client
from app.services.model_service import ModelService
from app.services.rag_service import RAGService
from app.services.session_service import SessionService
from app.services.ship30_service import Ship30Service

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMServiceProtocol(Protocol):
    """Protocol interface for LLM operations."""

    async def astream(self, messages: list[dict[str, str]], system_prompt: str | None = None, **kwargs: Any) -> Any: ...
    async def acomplete(self, messages: list[dict[str, str]], system_prompt: str | None = None, **kwargs: Any) -> str: ...
    async def astream_chat(self, messages: list[dict[str, str]], system_prompt: str | None = None, **kwargs: Any) -> Any: ...


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


def get_llm_service(
    settings: Settings = Depends(get_settings),
) -> BaseLLMClient:
    """Dependency provider for LLM client."""
    return get_llm_client(settings=settings)


def get_rag_service(
    settings: Settings = Depends(get_settings),
) -> RAGService:
    """Dependency provider for RAG service."""
    return RAGService(settings=settings)


def get_ship30_service(
    rag_service: RAGService = Depends(get_rag_service),
) -> Ship30Service:
    """Dependency provider for Ship30Service."""
    return Ship30Service(rag_service=rag_service)


def get_artifact_service() -> ArtifactService:
    """Dependency provider for ArtifactService."""
    return ArtifactService()


def get_health_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthService:
    """Dependency provider for HealthService."""
    return HealthService(db=db, settings=settings)


def get_model_service(
    settings: Settings = Depends(get_settings),
) -> ModelService:
    """Dependency provider for ModelService."""
    return ModelService(settings=settings)


def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repository),
) -> SessionService:
    """Dependency provider for SessionService."""
    return SessionService(session_repo=session_repo)


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    session_repo: SessionRepository = Depends(get_session_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    artifact_repo: ArtifactRepository = Depends(get_artifact_repository),
    rag_service: RAGService = Depends(get_rag_service),
    ship30_service: Ship30Service = Depends(get_ship30_service),
    artifact_service: ArtifactService = Depends(get_artifact_service),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    """Dependency provider for ChatService."""
    return ChatService(
        db=db,
        session_repo=session_repo,
        message_repo=message_repo,
        artifact_repo=artifact_repo,
        rag_service=rag_service,
        ship30_service=ship30_service,
        artifact_service=artifact_service,
        settings=settings,
    )
