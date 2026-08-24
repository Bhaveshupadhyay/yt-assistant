"""Tests for Repository CRUD operations with Enums."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import ArtifactType, MessageRole, ModelName
from app.repositories.artifact_repository import ArtifactRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository


@pytest.mark.asyncio
async def test_session_repository_crud(db_session: AsyncSession):
    """Test full CRUD operations on SessionRepository."""
    repo = SessionRepository(session=db_session)

    # 1. Create
    session = await repo.create(
        title="Brian Balfour Growth Loops",
        model_used=ModelName.CLAUDE_3_5_SONNET,
    )
    await db_session.commit()
    assert session.id is not None
    assert session.title == "Brian Balfour Growth Loops"

    # 2. Read by ID
    fetched = await repo.get_by_id(session.id)
    assert fetched is not None
    assert fetched.id == session.id

    # 3. List recent
    await repo.create(title="Session 2", model_used=ModelName.LLAMA_3_2)
    await db_session.commit()
    sessions = await repo.list_recent(limit=10)
    assert len(sessions) == 2

    # 4. Update
    updated = await repo.update(
        session_id=session.id,
        title="Updated Growth Loops Title",
        model_used=ModelName.GPT_4O,
    )
    await db_session.commit()
    assert updated is not None
    assert updated.title == "Updated Growth Loops Title"
    assert updated.model_used == ModelName.GPT_4O.value

    # 5. Delete
    deleted = await repo.delete(session.id)
    await db_session.commit()
    assert deleted is True
    assert await repo.get_by_id(session.id) is None


@pytest.mark.asyncio
async def test_message_repository_crud(db_session: AsyncSession):
    """Test CRUD operations on MessageRepository."""
    session_repo = SessionRepository(session=db_session)
    msg_repo = MessageRepository(session=db_session)

    session = await session_repo.create(title="Retention Strategies")
    await db_session.commit()

    # 1. Create User Message
    msg1 = await msg_repo.create(
        session_id=session.id,
        role=MessageRole.USER,
        content="How do I increase week 1 activation?",
    )

    # 2. Create Assistant Message with citations
    citations = [
        {
            "episode_title": "Casey Winters on Retention",
            "guest_name": "Casey Winters",
            "timestamp": "08:15",
            "snippet": "Activation is the bridge to retention.",
        }
    ]
    msg2 = await msg_repo.create(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content="Casey Winters notes that activation is the bridge to retention.",
        citations=citations,
        has_artifact=False,
    )
    await db_session.commit()

    # 3. List messages by session
    messages = await msg_repo.get_by_session_id(session.id)
    assert len(messages) == 2
    assert messages[0].id == msg1.id
    assert messages[1].id == msg2.id
    assert len(messages[1].citations) == 1

    # 4. Delete message
    deleted = await msg_repo.delete(msg1.id)
    await db_session.commit()
    assert deleted is True
    assert await msg_repo.get_by_id(msg1.id) is None


@pytest.mark.asyncio
async def test_artifact_repository_crud(db_session: AsyncSession):
    """Test CRUD operations on ArtifactRepository."""
    session_repo = SessionRepository(session=db_session)
    artifact_repo = ArtifactRepository(session=db_session)

    session = await session_repo.create(title="Ship 30 Essay Workshop")
    await db_session.commit()

    # 1. Create Artifact
    artifact = await artifact_repo.create(
        session_id=session.id,
        artifact_type=ArtifactType.MARKDOWN,
        title="Why PLG Fails Without Retention - Ship 30 Essay",
        content="# Why PLG Fails Without Retention\n\nMost founders believe...",
    )
    await db_session.commit()
    assert artifact.id is not None
    assert artifact.artifact_type == ArtifactType.MARKDOWN

    # 2. Fetch by ID
    fetched = await artifact_repo.get_by_id(artifact.id)
    assert fetched is not None
    assert fetched.title == "Why PLG Fails Without Retention - Ship 30 Essay"

    # 3. List by session ID
    artifacts = await artifact_repo.get_by_session_id(session.id)
    assert len(artifacts) == 1
    assert artifacts[0].id == artifact.id

    # 4. Delete
    deleted = await artifact_repo.delete(artifact.id)
    await db_session.commit()
    assert deleted is True
    assert await artifact_repo.get_by_id(artifact.id) is None
