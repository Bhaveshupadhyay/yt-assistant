"""Repository layer for Artifact database operations with ArtifactType Enum."""

from collections.abc import Sequence
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.enums import ArtifactType
from app.models.artifact import Artifact
from app.repositories.base import BaseRepository


class ArtifactRepository(BaseRepository[Artifact]):
    """Repository handling CRUD operations for Artifact."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Artifact, session)

    async def create(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType | str,
        title: str,
        content: str,
        message_id: uuid.UUID | None = None,
        artifact_id: uuid.UUID | None = None,
    ) -> Artifact:
        """Create and persist a new Artifact instance."""
        type_enum = artifact_type if isinstance(artifact_type, ArtifactType) else ArtifactType(artifact_type)
        artifact = Artifact(
            id=artifact_id or uuid.uuid4(),
            session_id=session_id,
            message_id=message_id,
            artifact_type=type_enum,
            title=title,
            content=content,
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def get_by_id(self, artifact_id: uuid.UUID) -> Artifact | None:
        """Retrieve an artifact by its UUID."""
        return await self.session.get(Artifact, artifact_id)

    async def get_by_session_id(self, session_id: uuid.UUID) -> Sequence[Artifact]:
        """Fetch all artifacts for a session ordered by created_at descending."""
        stmt = (
            select(Artifact)
            .where(Artifact.session_id == session_id)
            .order_by(desc(Artifact.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete(self, artifact_id: uuid.UUID) -> bool:
        """Delete an artifact by its UUID."""
        artifact = await self.get_by_id(artifact_id)
        if not artifact:
            return False
        await self.session.delete(artifact)
        await self.session.flush()
        return True
