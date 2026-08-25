"""Unit tests for SessionService in isolation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from app.core.exceptions import SessionNotFoundException
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionUpdate
from app.services.session_service import SessionService


@pytest.mark.asyncio
async def test_session_service_create_and_get():
    """Verify SessionService creates and retrieves session models."""
    mock_repo = AsyncMock(spec=SessionRepository)
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    mock_session_obj = MagicMock()
    mock_session_obj.id = session_id
    mock_session_obj.title = "Test Session"
    mock_session_obj.model_used = "claude-3-5-sonnet"
    mock_session_obj.created_at = now
    mock_session_obj.updated_at = now
    mock_session_obj.messages = []
    mock_session_obj.artifacts = []

    mock_repo.create.return_value = mock_session_obj
    mock_repo.get_by_id.return_value = mock_session_obj

    service = SessionService(session_repo=mock_repo)

    create_res = await service.create_session(SessionCreate(title="Test Session", model_used="claude-3-5-sonnet"))
    assert create_res.id == session_id
    assert create_res.title == "Test Session"

    get_res = await service.get_session(session_id)
    assert get_res.id == session_id


@pytest.mark.asyncio
async def test_session_service_not_found_raises_exception():
    """Verify SessionService raises SessionNotFoundException when ID is absent."""
    mock_repo = AsyncMock(spec=SessionRepository)
    mock_repo.get_by_id.return_value = None
    mock_repo.update.return_value = None
    mock_repo.delete.return_value = False

    service = SessionService(session_repo=mock_repo)
    missing_id = uuid.uuid4()

    with pytest.raises(SessionNotFoundException):
        await service.get_session(missing_id)

    with pytest.raises(SessionNotFoundException):
        await service.update_session(missing_id, SessionUpdate(title="New"))

    with pytest.raises(SessionNotFoundException):
        await service.delete_session(missing_id)
