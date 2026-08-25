"""Automated pytest suite for health and liveness endpoints (Task 5.2)."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import HealthStatus


@pytest.mark.asyncio
async def test_root_health_endpoint_success(async_client: AsyncClient):
    """Verify GET /health returns OK when database and Ollama are reachable."""
    with patch("app.api.v1.health.get_ollama_client") as mock_ollama_factory:
        mock_client = AsyncMock()
        mock_client.get.return_value = httpx.Response(200, json={"models": []})
        mock_ollama_factory.return_value = mock_client

        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == HealthStatus.OK.value
        assert data["database"] is True
        assert data["ollama"] is True
        assert "version" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_v1_health_endpoint_degraded_when_ollama_offline(async_client: AsyncClient):
    """Verify GET /api/v1/health returns DEGRADED status when Ollama is unreachable."""
    with patch("app.api.v1.health.get_ollama_client") as mock_ollama_factory:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_ollama_factory.return_value = mock_client

        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == HealthStatus.DEGRADED.value
        assert data["database"] is True
        assert data["ollama"] is False


@pytest.mark.asyncio
async def test_health_endpoint_database_failure(async_client: AsyncClient):
    """Verify health endpoint reports database: False if DB query raises exception."""
    with patch("app.api.v1.health.get_ollama_client") as mock_ollama_factory:
        mock_client = AsyncMock()
        mock_client.get.return_value = httpx.Response(200, json={"models": []})
        mock_ollama_factory.return_value = mock_client

        # Mock DB failure
        with patch.object(AsyncSession, "execute", side_effect=Exception("DB pool timeout")):
            response = await async_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["database"] is False
            assert data["status"] == HealthStatus.DEGRADED.value
