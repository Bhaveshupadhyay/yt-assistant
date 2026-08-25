"""Unit tests for HealthService."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings
from app.core.enums import HealthStatus
from app.services.health_service import HealthService


@pytest.mark.asyncio
async def test_health_service_check_health_ok():
    """Verify HealthService returns OK when both DB and Ollama are healthy."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_db.execute.return_value = mock_result

    settings = Settings(APP_VERSION="1.0.0", OLLAMA_BASE_URL="http://localhost:11434")
    service = HealthService(db=mock_db, settings=settings)

    with patch("app.services.health_service.get_ollama_client") as mock_ollama_factory:
        mock_ollama = AsyncMock()
        mock_ollama.get.return_value = httpx.Response(200, json={"models": []})
        mock_ollama_factory.return_value = mock_ollama

        health = await service.check_health()
        assert health.status == HealthStatus.OK
        assert health.database is True
        assert health.ollama is True
        assert health.version == "1.0.0"


@pytest.mark.asyncio
async def test_health_service_check_health_degraded_db_failure():
    """Verify HealthService returns DEGRADED when database fails."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.side_effect = Exception("DB connection timeout")

    settings = Settings(APP_VERSION="1.0.0")
    service = HealthService(db=mock_db, settings=settings)

    with patch("app.services.health_service.get_ollama_client") as mock_ollama_factory:
        mock_ollama = AsyncMock()
        mock_ollama.get.return_value = httpx.Response(200, json={"models": []})
        mock_ollama_factory.return_value = mock_ollama

        health = await service.check_health()
        assert health.status == HealthStatus.DEGRADED
        assert health.database is False
        assert health.ollama is True
