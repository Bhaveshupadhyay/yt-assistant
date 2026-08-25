"""Pytest fixtures for backend tests."""

from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
import logging
from app.core.config import Settings, get_settings
from app.core.database import Base
from app.core.dependencies import get_db
from main import create_application

logging.getLogger("aiosqlite").setLevel(logging.WARNING)


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing isolated test settings."""
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        DATABASE_ECHO=False,
        DEBUG=True,
        ENVIRONMENT="testing",
        LOG_FORMAT="console",
    )


@pytest_asyncio.fixture
async def test_engine(test_settings: Settings) -> AsyncGenerator[AsyncEngine, None]:
    """Fixture providing an in-memory SQLite async engine."""
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Fixture providing an isolated AsyncSession."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def app_instance(test_settings: Settings, test_engine: AsyncEngine, db_session: AsyncSession):
    """Fixture providing a configured FastAPI app instance with overridden dependencies."""
    app = create_application()

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(app_instance) -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing an AsyncClient running inside the application lifespan context."""
    transport = ASGITransport(app=app_instance)
    async with app_instance.router.lifespan_context(app_instance):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
