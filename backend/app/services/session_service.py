"""Service for managing chat session lifecycles, message retrieval, and updates."""

from collections.abc import Sequence
import logging
import uuid
from app.core.exceptions import SessionNotFoundException
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionDetail, SessionRead, SessionUpdate

logger = logging.getLogger(__name__)


class SessionService:
    """Service encapsulating business operations and validations for chat sessions."""

    def __init__(self, session_repo: SessionRepository) -> None:
        """Initialize SessionService.

        Args:
            session_repo: Active SessionRepository instance.
        """
        self.session_repo = session_repo

    async def create_session(self, payload: SessionCreate) -> SessionRead:
        """Create a new conversational session.

        Args:
            payload: SessionCreate data.

        Returns:
            SessionRead: The created session representation.
        """
        session = await self.session_repo.create(
            title=payload.title,
            model_used=payload.model_used,
        )
        return SessionRead.model_validate(session)

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> Sequence[SessionRead]:
        """Retrieve recent chat sessions with pagination.

        Args:
            limit: Maximum items to return.
            offset: Number of items to skip.

        Returns:
            Sequence[SessionRead]: Paginated list of sessions.
        """
        sessions = await self.session_repo.list_recent(limit=limit, offset=offset)
        return [SessionRead.model_validate(s) for s in sessions]

    async def get_session(self, session_id: uuid.UUID) -> SessionDetail:
        """Retrieve a single session by ID with its messages and artifacts.

        Args:
            session_id: Unique session UUID.

        Returns:
            SessionDetail: Full session details.

        Raises:
            SessionNotFoundException: If the session does not exist.
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise SessionNotFoundException(session_id=session_id)
        return SessionDetail.model_validate(session)

    async def update_session(self, session_id: uuid.UUID, payload: SessionUpdate) -> SessionRead:
        """Update metadata for an existing chat session.

        Args:
            session_id: Unique session UUID.
            payload: SessionUpdate data.

        Returns:
            SessionRead: Updated session representation.

        Raises:
            SessionNotFoundException: If the session does not exist.
        """
        session = await self.session_repo.update(
            session_id=session_id,
            title=payload.title,
            model_used=payload.model_used,
        )
        if not session:
            raise SessionNotFoundException(session_id=session_id)
        return SessionRead.model_validate(session)

    async def delete_session(self, session_id: uuid.UUID) -> None:
        """Delete a chat session along with associated messages and artifacts.

        Args:
            session_id: Unique session UUID.

        Raises:
            SessionNotFoundException: If the session does not exist.
        """
        deleted = await self.session_repo.delete(session_id=session_id)
        if not deleted:
            raise SessionNotFoundException(session_id=session_id)
