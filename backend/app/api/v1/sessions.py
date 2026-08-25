"""Chat session management router."""

from collections.abc import Sequence
import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import get_session_service
from app.schemas.session import SessionCreate, SessionDetail, SessionRead, SessionUpdate
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    payload: SessionCreate,
    session_service: SessionService = Depends(get_session_service),
) -> SessionRead:
    """Create a new conversational session."""
    return await session_service.create_session(payload=payload)


@router.get(
    "",
    response_model=list[SessionRead],
    status_code=status.HTTP_200_OK,
    summary="List recent chat sessions",
)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session_service: SessionService = Depends(get_session_service),
) -> Sequence[SessionRead]:
    """Retrieve recent chat sessions with pagination."""
    return await session_service.list_sessions(limit=limit, offset=offset)


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    status_code=status.HTTP_200_OK,
    summary="Get chat session details and message history",
)
async def get_session(
    session_id: uuid.UUID,
    session_service: SessionService = Depends(get_session_service),
) -> SessionDetail:
    """Retrieve a single session by ID with its messages and artifacts."""
    return await session_service.get_session(session_id=session_id)


@router.patch(
    "/{session_id}",
    response_model=SessionRead,
    status_code=status.HTTP_200_OK,
    summary="Update session title or active model",
)
async def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    session_service: SessionService = Depends(get_session_service),
) -> SessionRead:
    """Update metadata for an existing chat session."""
    return await session_service.update_session(session_id=session_id, payload=payload)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: uuid.UUID,
    session_service: SessionService = Depends(get_session_service),
) -> None:
    """Delete a chat session along with associated messages and artifacts."""
    await session_service.delete_session(session_id=session_id)
