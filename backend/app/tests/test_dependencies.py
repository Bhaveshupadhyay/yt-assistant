"""Tests for Dependency Injection providers."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings
from app.core.dependencies import (
    get_artifact_repository,
    get_llm_service,
    get_message_repository,
    get_rag_service,
    get_session_repository,
)
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository


def test_repository_dependencies(db_session: AsyncSession):
    """Verify repository providers return correctly initialized instances."""
    session_repo = get_session_repository(db=db_session)
    assert isinstance(session_repo, SessionRepository)
    assert session_repo.session is db_session

    msg_repo = get_message_repository(db=db_session)
    assert isinstance(msg_repo, MessageRepository)
    assert msg_repo.session is db_session

    art_repo = get_artifact_repository(db=db_session)
    assert isinstance(art_repo, ArtifactRepository)
    assert art_repo.session is db_session


def test_service_dependencies():
    """Verify LLM and RAG service providers return instances conforming to protocols."""
    settings = Settings()
    llm_service = get_llm_service(settings=settings)
    rag_service = get_rag_service(settings=settings)

    assert llm_service is not None
    assert rag_service is not None
