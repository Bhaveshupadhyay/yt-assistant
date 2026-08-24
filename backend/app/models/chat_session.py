"""ChatSession database model with ModelName constants."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.enums import ModelName

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.message import Message


class ChatSession(Base):
    """SQLAlchemy model representing a conversation session."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Conversation",
    )
    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=ModelName.CLAUDE_3_5_SONNET.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Artifact.created_at",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, title='{self.title}', model_used='{self.model_used}')>"
