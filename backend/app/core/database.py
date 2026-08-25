"""SQLAlchemy 2.0 Async database engine and session management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, StaticPool
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    pass


def get_engine_args(settings: Settings) -> dict[str, Any]:
    """Builds appropriate engine configuration arguments based on DB dialect."""
    engine_kwargs: dict[str, Any] = {
        "echo": settings.DATABASE_ECHO,
        "future": True,
    }

    if settings.is_sqlite:
        # SQLite specific options
        if ":memory:" in settings.DATABASE_URL:
            engine_kwargs["poolclass"] = StaticPool
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL specific pool options
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    return engine_kwargs


def create_engine_and_session_factory(
    settings: Settings | None = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Creates the SQLAlchemy async engine and session factory."""
    current_settings = settings or get_settings()
    engine_args = get_engine_args(current_settings)

    db_engine = create_async_engine(current_settings.DATABASE_URL, **engine_args)

    # Enable foreign keys for SQLite
    if current_settings.is_sqlite:

        @event.listens_for(db_engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    return db_engine, session_factory


# Initialize global engine and session factory
_settings = get_settings()
engine, async_session_factory = create_engine_and_session_factory(_settings)


async def init_db(engine_instance: AsyncEngine | None = None) -> None:
    """Creates all database tables defined in metadata if they don't exist."""
    target_engine = engine_instance or engine
    logger.info("Initializing database tables...")
    async with target_engine.begin() as conn:
        # Import models so they are registered with Base.metadata
        import app.models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")


async def close_db(engine_instance: AsyncEngine | None = None) -> None:
    """Disposes of the database engine connection pool."""
    target_engine = engine_instance or engine
    logger.info("Disposing database engine connections...")
    await target_engine.dispose()
    logger.info("Database connections disposed.")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for obtaining an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
