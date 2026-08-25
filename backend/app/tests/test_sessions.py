"""Automated pytest suite for CRUD session management & persistence (Task 5.2)."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import ArtifactType, MessageRole, ModelName
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.message_repository import MessageRepository


@pytest.mark.asyncio
async def test_create_session(async_client: AsyncClient):
    """Verify creating a new chat session via POST /api/v1/sessions."""
    payload = {
        "title": "B2B Retention Strategy",
        "model_used": ModelName.CLAUDE_3_5_SONNET.value,
    }
    response = await async_client.post("/api/v1/sessions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == "B2B Retention Strategy"
    assert data["model_used"] == ModelName.CLAUDE_3_5_SONNET.value
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_list_sessions_pagination(async_client: AsyncClient):
    """Verify listing sessions with limit and offset query parameters."""
    for i in range(5):
        await async_client.post("/api/v1/sessions", json={"title": f"Session {i}"})

    resp = await async_client.get("/api/v1/sessions?limit=3&offset=0")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3

    resp_offset = await async_client.get("/api/v1/sessions?limit=3&offset=3")
    assert resp_offset.status_code == 200
    offset_items = resp_offset.json()
    assert len(offset_items) >= 2


@pytest.mark.asyncio
async def test_get_session_full_history(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /api/v1/sessions/{id} returns message and artifact history in chronological order."""
    # 1. Create Session
    create_resp = await async_client.post("/api/v1/sessions", json={"title": "Artifact & Chat Session"})
    session_id = uuid.UUID(create_resp.json()["id"])

    # 2. Add Messages & Artifact directly via repositories
    msg_repo = MessageRepository(db_session)
    art_repo = ArtifactRepository(db_session)

    user_msg = await msg_repo.create(
        session_id=session_id,
        role=MessageRole.USER,
        content="Give me a PLG checklist.",
    )
    asst_msg = await msg_repo.create(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content="Here is your PLG onboarding checklist.",
        citations=[
            {
                "episode_title": "Elena Verna on PLG",
                "guest_name": "Elena Verna",
                "timestamp": "00:04:15",
                "youtube_url": "https://youtube.com/watch?v=123",
                "snippet": "Self-serve loops are essential.",
            }
        ],
        has_artifact=True,
    )
    await art_repo.create(
        session_id=session_id,
        artifact_type=ArtifactType.HTML,
        title="PLG Checklist",
        content="<!DOCTYPE html><html><body>PLG Checklist</body></html>",
        message_id=asst_msg.id,
    )
    await db_session.commit()

    # 3. Retrieve Session Details via API
    get_resp = await async_client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["id"] == str(session_id)
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
    assert len(data["messages"][1]["citations"]) == 1
    assert data["messages"][1]["citations"][0]["guest_name"] == "Elena Verna"

    assert len(data["artifacts"]) == 1
    assert data["artifacts"][0]["title"] == "PLG Checklist"
    assert data["artifacts"][0]["artifact_type"] == "html"
    assert data["artifacts"][0]["message_id"] == str(asst_msg.id)


@pytest.mark.asyncio
async def test_update_and_delete_session(async_client: AsyncClient):
    """Verify PATCH and DELETE operations on chat sessions."""
    # Create
    create_resp = await async_client.post("/api/v1/sessions", json={"title": "Old Session Title"})
    session_id = create_resp.json()["id"]

    # Patch Title & Model
    patch_resp = await async_client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"title": "Updated Session Title", "model_used": ModelName.LLAMA_3_2.value},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated Session Title"
    assert patch_resp.json()["model_used"] == ModelName.LLAMA_3_2.value

    # Delete
    del_resp = await async_client.delete(f"/api/v1/sessions/{session_id}")
    assert del_resp.status_code == 204

    # Verify 404
    get_resp = await async_client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404
    assert get_resp.json()["error"]["type"] == "SessionNotFoundException"
