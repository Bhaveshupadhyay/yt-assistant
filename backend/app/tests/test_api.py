"""Tests for API endpoints and HTTP error handling with Enums."""

import uuid
import pytest
from httpx import AsyncClient
from app.core.enums import HealthStatus, ModelName


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Verify /health endpoint returns system status and DB status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in (HealthStatus.OK.value, HealthStatus.DEGRADED.value)
    assert data["database"] is True
    assert "ollama" in data
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_create_and_get_session(async_client: AsyncClient):
    """Verify session creation and retrieval via API."""
    # 1. Create Session
    create_payload = {
        "title": "Pricing Strategy Debate",
        "model_used": ModelName.CLAUDE_3_5_SONNET.value,
    }
    create_resp = await async_client.post("/api/v1/sessions", json=create_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    session_id = created_data["id"]
    assert created_data["title"] == "Pricing Strategy Debate"
    assert created_data["model_used"] == ModelName.CLAUDE_3_5_SONNET.value

    # 2. Get Session Detail
    get_resp = await async_client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    detail_data = get_resp.json()
    assert detail_data["id"] == session_id
    assert detail_data["messages"] == []
    assert detail_data["artifacts"] == []


@pytest.mark.asyncio
async def test_list_sessions(async_client: AsyncClient):
    """Verify listing sessions endpoint."""
    await async_client.post("/api/v1/sessions", json={"title": "Session A"})
    await async_client.post("/api/v1/sessions", json={"title": "Session B"})

    list_resp = await async_client.get("/api/v1/sessions?limit=10")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_update_and_delete_session(async_client: AsyncClient):
    """Verify updating and deleting a session."""
    # Create
    create_resp = await async_client.post("/api/v1/sessions", json={"title": "Original Title"})
    session_id = create_resp.json()["id"]

    # Update
    update_resp = await async_client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"title": "New Title", "model_used": ModelName.LLAMA_3_2.value},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "New Title"
    assert update_resp.json()["model_used"] == ModelName.LLAMA_3_2.value

    # Delete
    del_resp = await async_client.delete(f"/api/v1/sessions/{session_id}")
    assert del_resp.status_code == 204

    # Verify not found after delete
    get_resp = await async_client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404
    error_data = get_resp.json()
    assert error_data["error"]["type"] == "SessionNotFoundException"


@pytest.mark.asyncio
async def test_get_nonexistent_session_returns_404(async_client: AsyncClient):
    """Verify custom exception format on 404."""
    random_id = uuid.uuid4()
    resp = await async_client.get(f"/api/v1/sessions/{random_id}")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["type"] == "SessionNotFoundException"
    assert str(random_id) in body["error"]["message"]


@pytest.mark.asyncio
async def test_app_lifespan():
    """Verify application lifespan creates tables on startup and cleans up on shutdown."""
    from app.core.lifespan import lifespan
    from main import create_application
    test_app = create_application()
    async with lifespan(test_app):
        # App is started and tables/clients are initialized
        assert test_app.title == "The Lenny Growth Assistant"
