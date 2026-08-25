"""Chat session management router."""

from collections.abc import Sequence
import uuid
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import get_session_repository
from app.core.exceptions import SessionNotFoundException
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionDetail, SessionRead, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    payload: SessionCreate,
    session_repo: SessionRepository = Depends(get_session_repository),
) -> SessionRead:
    """Create a new conversational session."""
    session = await session_repo.create(
        title=payload.title,
        model_used=payload.model_used,
    )
    return SessionRead.model_validate(session)


@router.get(
    "",
    response_model=list[SessionRead],
    status_code=status.HTTP_200_OK,
    summary="List recent chat sessions",
)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session_repo: SessionRepository = Depends(get_session_repository),
) -> Sequence[SessionRead]:
    """Retrieve recent chat sessions with pagination."""
    sessions = await session_repo.list_recent(limit=limit, offset=offset)
    return [SessionRead.model_validate(s) for s in sessions]


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    status_code=status.HTTP_200_OK,
    summary="Get chat session details and message history",
)
async def get_session(
    session_id: uuid.UUID,
    session_repo: SessionRepository = Depends(get_session_repository),
) -> SessionDetail:
    """Retrieve a single session by ID with its messages and artifacts."""
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise SessionNotFoundException(session_id=session_id)
    return SessionDetail.model_validate(session)


@router.patch(
    "/{session_id}",
    response_model=SessionRead,
    status_code=status.HTTP_200_OK,
    summary="Update session title or active model",
)
async def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    session_repo: SessionRepository = Depends(get_session_repository),
) -> SessionRead:
    """Update metadata for an existing chat session."""
    session = await session_repo.update(
        session_id=session_id,
        title=payload.title,
        model_used=payload.model_used,
    )
    if not session:
        raise SessionNotFoundException(session_id=session_id)
    return SessionRead.model_validate(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: uuid.UUID,
    session_repo: SessionRepository = Depends(get_session_repository),
) -> None:
    """Delete a chat session along with associated messages and artifacts."""
    deleted = await session_repo.delete(session_id=session_id)
    if not deleted:
        raise SessionNotFoundException(session_id=session_id)
