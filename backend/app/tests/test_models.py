"""Tests for SQLAlchemy ORM models with typed Enums."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import ArtifactType, MessageRole, ModelName
from app.models.artifact import Artifact
from app.models.chat_session import ChatSession
from app.models.message import Message


@pytest.mark.asyncio
async def test_create_chat_session_model(db_session: AsyncSession):
    """Verify ChatSession model instantiation and defaults."""
    session = ChatSession(
        title="Elena Verna Retention Deep Dive",
        model_used=ModelName.LLAMA_3_2.value,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert isinstance(session.id, uuid.UUID)
    assert session.title == "Elena Verna Retention Deep Dive"
    assert session.model_used == ModelName.LLAMA_3_2.value
    assert session.created_at is not None
    assert session.updated_at is not None


@pytest.mark.asyncio
async def test_create_message_with_json_citations(db_session: AsyncSession):
    """Verify Message model handles JSON citations and relationships."""
    session = ChatSession(title="Product Growth Q&A")
    db_session.add(session)
    await db_session.commit()

    citations_data = [
        {
            "episode_title": "Elena Verna on B2B Growth & PLG",
            "guest_name": "Elena Verna",
            "guest_role": "Head of Growth",
            "timestamp": "14:20",
            "youtube_url": "https://youtube.com/watch?v=123",
            "snippet": "Retention is a product loop, not a marketing hack.",
        }
    ]

    message = Message(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="Elena Verna emphasizes that retention is built into the core product loops.",
        citations=citations_data,
        has_artifact=True,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    assert message.session_id == session.id
    assert message.role == MessageRole.ASSISTANT
    assert len(message.citations) == 1
    assert message.citations[0]["guest_name"] == "Elena Verna"
    assert message.has_artifact is True


@pytest.mark.asyncio
async def test_create_artifact_model(db_session: AsyncSession):
    """Verify Artifact model instantiation and foreign key relationships."""
    session = ChatSession(title="Pricing Calculator Session")
    db_session.add(session)
    await db_session.commit()

    message = Message(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="Here is your interactive pricing calculator widget.",
        has_artifact=True,
    )
    db_session.add(message)
    await db_session.commit()

    artifact = Artifact(
        session_id=session.id,
        message_id=message.id,
        artifact_type=ArtifactType.HTML,
        title="Interactive SaaS Pricing Calculator",
        content="<div class='calculator'><h1>Pricing Widget</h1></div>",
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    assert artifact.session_id == session.id
    assert artifact.message_id == message.id
    assert artifact.artifact_type == ArtifactType.HTML
    assert "Pricing Widget" in artifact.content


@pytest.mark.asyncio
async def test_session_cascade_delete(db_session: AsyncSession):
    """Verify deleting a ChatSession cascades and removes associated messages and artifacts."""
    session = ChatSession(title="Temporary Session")
    db_session.add(session)
    await db_session.commit()

    message = Message(
        session_id=session.id,
        role=MessageRole.USER,
        content="How do I launch?",
    )
    db_session.add(message)
    await db_session.commit()

    artifact = Artifact(
        session_id=session.id,
        message_id=message.id,
        artifact_type=ArtifactType.MARKDOWN,
        title="Launch Checklist",
        content="# Launch Checklist",
    )
    db_session.add(artifact)
    await db_session.commit()

    # Delete session
    await db_session.delete(session)
    await db_session.commit()

    # Verify messages and artifacts are removed
    fetched_message = await db_session.get(Message, message.id)
    fetched_artifact = await db_session.get(Artifact, artifact.id)

    assert fetched_message is None
    assert fetched_artifact is None
