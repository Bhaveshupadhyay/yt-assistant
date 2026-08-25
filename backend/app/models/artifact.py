"""Artifact database model with typed Enums and composite referential integrity."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.enums import ArtifactType

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession
    from app.models.message import Message


class Artifact(Base):
    """SQLAlchemy model representing an interactive widget, essay, or diagram artifact."""

    __tablename__ = "artifacts"
    __table_args__ = (
        CheckConstraint(
            f"artifact_type IN ({', '.join(repr(t.value) for t in ArtifactType)})",
            name="chk_artifact_type",
        ),
        ForeignKeyConstraint(
            ["message_id", "session_id"],
            ["messages.id", "messages.session_id"],
            name="fk_artifacts_message_session",
            ondelete="SET NULL",
        ),
        Index("idx_artifacts_session_id", "session_id"),
        Index("idx_artifacts_message_id", "message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(
        SAEnum(ArtifactType, native_enum=False, length=50, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="artifacts",
        foreign_keys=[session_id],
    )
    message: Mapped["Message | None"] = relationship(
        "Message",
        back_populates="artifacts",
        foreign_keys=[message_id, session_id],
        overlaps="session,artifacts",
    )

    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, type='{self.artifact_type}', title='{self.title}')>"
