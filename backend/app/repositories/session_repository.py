"""Repository layer for ChatSession database operations."""

from collections.abc import Sequence
from datetime import datetime, timezone
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import ModelName
from app.models.chat_session import ChatSession
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[ChatSession]):
    """Repository handling CRUD operations for ChatSession."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChatSession, session)

    async def create(
        self,
        title: str = "New Conversation",
        model_used: str | ModelName = ModelName.CLAUDE_3_5_SONNET,
        session_id: uuid.UUID | None = None,
    ) -> ChatSession:
        """Create and add a new ChatSession instance."""
        model_val = model_used.value if isinstance(model_used, ModelName) else str(model_used)
        chat_session = ChatSession(
            id=session_id or uuid.uuid4(),
            title=title,
            model_used=model_val,
        )
        self.session.add(chat_session)
        await self.session.flush()
        return chat_session

    async def get_by_id(self, session_id: uuid.UUID) -> ChatSession | None:
        """Retrieve a session by its UUID."""
        return await self.session.get(ChatSession, session_id)

    async def get_or_create(
        self,
        session_id: uuid.UUID,
        title: str = "New Conversation",
        model_used: str | ModelName = ModelName.GEMINI_3_6_FLASH,
    ) -> ChatSession:
        """Retrieve existing session or automatically create a new one with given session_id."""
        existing = await self.get_by_id(session_id)
        if existing:
            return existing
        return await self.create(title=title, model_used=model_used, session_id=session_id)

    async def list_recent(self, limit: int = 50, offset: int = 0) -> Sequence[ChatSession]:
        """List sessions ordered by updated_at descending."""
        stmt = (
            select(ChatSession)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(
        self,
        session_id: uuid.UUID,
        title: str | None = None,
        model_used: str | ModelName | None = None,
    ) -> ChatSession | None:
        """Update fields of an existing ChatSession."""
        chat_session = await self.get_by_id(session_id)
        if not chat_session:
            return None

        if title is not None:
            chat_session.title = title
        if model_used is not None:
            chat_session.model_used = model_used.value if isinstance(model_used, ModelName) else str(model_used)

        chat_session.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return chat_session

    async def delete(self, session_id: uuid.UUID) -> bool:
        """Delete a chat session by ID (cascades to messages and artifacts)."""
        chat_session = await self.get_by_id(session_id)
        if not chat_session:
            return False
        await self.session.delete(chat_session)
        await self.session.flush()
        return True
