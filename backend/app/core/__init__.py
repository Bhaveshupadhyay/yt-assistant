"""Core infrastructure module containing config, database, logging, exceptions, enums, and dependencies."""

from app.core.clients import (
    close_all_clients,
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
from app.core.config import Settings, get_settings
from app.core.database import Base, async_session_factory, engine, get_db_session, init_db
from app.core.enums import (
    ArtifactType,
    Environment,
    HealthStatus,
    LogFormat,
    LogLevel,
    MessageRole,
    ModelName,
    ModelProvider,
)
from app.core.exceptions import (
    AppException,
    ArtifactNotFoundException,
    DatabaseException,
    MessageNotFoundException,
    ModelProviderException,
    OllamaUnavailableException,
    SessionNotFoundException,
    TranscriptNotFoundException,
    ValidationException,
)
from app.core.lifespan import lifespan
from app.core.logging import get_logger, setup_logging

__all__ = [
    "lifespan",
    "Settings",
    "get_settings",
    "Base",
    "engine",
    "async_session_factory",
    "init_db",
    "get_db_session",
    "get_async_engine",
    "get_session_factory",
    "get_qdrant_client",
    "close_qdrant_client",
    "get_embedding_model",
    "get_ollama_client",
    "get_anthropic_client",
    "get_openai_client",
    "init_all_clients",
    "close_all_clients",
    "setup_logging",
    "get_logger",
    "ArtifactType",
    "MessageRole",
    "ModelProvider",
    "ModelName",
    "Environment",
    "LogFormat",
    "LogLevel",
    "HealthStatus",
    "AppException",
    "OllamaUnavailableException",
    "TranscriptNotFoundException",
    "SessionNotFoundException",
    "MessageNotFoundException",
    "ArtifactNotFoundException",
    "ModelProviderException",
    "DatabaseException",
    "ValidationException",
]
