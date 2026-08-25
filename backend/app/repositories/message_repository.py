"""Repository layer for Message database operations with MessageRole Enum."""

from collections.abc import Sequence
from typing import Any
import uuid
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import MessageRole
from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository handling CRUD operations for Message."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Message, session)

    async def create(
        self,
        session_id: uuid.UUID,
        role: MessageRole | str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
        has_artifact: bool = False,
        message_id: uuid.UUID | None = None,
    ) -> Message:
        """Create and add a new Message instance."""
        role_enum = role if isinstance(role, MessageRole) else MessageRole(role)
        message = Message(
            id=message_id or uuid.uuid4(),
            session_id=session_id,
            role=role_enum,
            content=content,
            citations=citations or [],
            has_artifact=has_artifact,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_by_id(self, message_id: uuid.UUID) -> Message | None:
        """Retrieve a message by its UUID."""
        return await self.session.get(Message, message_id)

    async def get_by_session_id(
        self,
        session_id: uuid.UUID,
        limit: int = 100,
    ) -> Sequence[Message]:
        """Fetch all messages for a session ordered chronologically."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(asc(Message.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recent_history(
        self,
        session_id: uuid.UUID,
        limit: int = 20,
        exclude_id: uuid.UUID | None = None,
    ) -> list[Message]:
        """Fetch the most recent N messages for a session in chronological order, optionally excluding a specific message ID."""
        stmt = select(Message).where(Message.session_id == session_id)
        if exclude_id is not None:
            stmt = stmt.where(Message.id != exclude_id)
        stmt = stmt.order_by(desc(Message.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def delete(self, message_id: uuid.UUID) -> bool:
        """Delete a message by its UUID."""
        message = await self.get_by_id(message_id)
        if not message:
            return False
        await self.session.delete(message)
        await self.session.flush()
        return True
