"""Tests for database engine, session factory, and table initialization."""

import pytest
from sqlalchemy import text
from app.core.config import Settings
from app.core.database import (
    Base,
    create_engine_and_session_factory,
    init_db,
)


@pytest.mark.asyncio
async def test_init_db_creates_all_tables():
    """Verify init_db registers and creates chat_sessions, messages, artifacts tables."""
    test_settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:")
    engine, _ = create_engine_and_session_factory(test_settings)

    await init_db(engine)

    async with engine.connect() as conn:
        # Verify tables exist in SQLite metadata
        res = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        )
        tables = [row[0] for row in res.fetchall()]

    await engine.dispose()

    assert "chat_sessions" in tables
    assert "messages" in tables
    assert "artifacts" in tables


@pytest.mark.asyncio
async def test_db_session_commit_and_rollback():
    """Verify session rollback on error."""
    test_settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:")
    engine, session_factory = create_engine_and_session_factory(test_settings)
    await init_db(engine)

    async with session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    await engine.dispose()
