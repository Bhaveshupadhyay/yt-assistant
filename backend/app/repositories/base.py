"""Generic base repository defining common CRUD operations."""

from typing import Generic, Sequence, Type, TypeVar
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing basic query operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id_val: uuid.UUID) -> ModelType | None:
        """Fetch an entity by primary key UUID."""
        return await self.session.get(self.model, id_val)

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelType]:
        """Fetch entities with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete(self, id_val: uuid.UUID) -> bool:
        """Delete an entity by primary key UUID."""
        entity = await self.get_by_id(id_val)
        if entity is None:
            return False
        await self.session.delete(entity)
        return True
