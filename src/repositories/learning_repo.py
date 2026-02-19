from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import LearningResource
from src.repositories.base import BaseRepository


class LearningRepository(BaseRepository):
    model = LearningResource

    async def get_user_resources(
        self,
        user_id: int,
        completed: bool | None = None,
        limit: int = 50,
    ) -> list[LearningResource]:
        stmt = select(LearningResource).where(LearningResource.user_id == user_id)
        if completed is not None:
            stmt = stmt.where(LearningResource.is_completed == completed)
        stmt = stmt.order_by(LearningResource.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_completed(self, resource_id: int) -> LearningResource | None:
        resource = await self.get_by_id(resource_id)
        if not resource:
            return None
        resource.is_completed = True
        resource.completed_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(resource)
        return resource

    async def count_completed_by_topic(
        self, user_id: int, topic_query: str
    ) -> int:
        topic = (topic_query or "").strip().lower()
        if not topic:
            return 0
        stmt = (
            select(LearningResource)
            .where(
                and_(
                    LearningResource.user_id == user_id,
                    LearningResource.is_completed == True,
                )
            )
            .order_by(LearningResource.created_at.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return sum(
            1 for r in rows
            if topic in (r.topic or "").lower() or topic in (r.title or "").lower()
        )
