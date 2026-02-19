from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.gamification import XPEvent
from src.repositories.base import BaseRepository


class XPRepository(BaseRepository):
    model = XPEvent

    async def create_event(
        self,
        user_id: int,
        event_type: str,
        xp_amount: int,
        source_type: str | None = None,
        source_id: int | None = None,
        description: str | None = None,
    ) -> XPEvent:
        return await self.create(
            user_id=user_id,
            event_type=event_type,
            xp_amount=xp_amount,
            source_type=source_type,
            source_id=source_id,
            description=description,
        )

    async def sum_positive_xp(self, user_id: int, since: datetime) -> int:
        stmt = select(func.coalesce(func.sum(XPEvent.xp_amount), 0)).where(
            and_(
                XPEvent.user_id == user_id,
                XPEvent.xp_amount > 0,
                XPEvent.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def sum_negative_xp(self, user_id: int, since: datetime) -> int:
        stmt = select(func.coalesce(func.sum(XPEvent.xp_amount), 0)).where(
            and_(
                XPEvent.user_id == user_id,
                XPEvent.xp_amount < 0,
                XPEvent.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_active_days_count(
        self, user_id: int, since: datetime
    ) -> int:
        stmt = (
            select(func.count(func.distinct(func.date(XPEvent.created_at))))
            .where(
                and_(
                    XPEvent.user_id == user_id,
                    XPEvent.created_at >= since,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_events(
        self, user_id: int, event_type: str, since: datetime
    ) -> int:
        stmt = select(func.count()).where(
            and_(
                XPEvent.user_id == user_id,
                XPEvent.event_type == event_type,
                XPEvent.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_recent_events(
        self, user_id: int, limit: int = 20
    ) -> list[XPEvent]:
        stmt = (
            select(XPEvent)
            .where(XPEvent.user_id == user_id)
            .order_by(XPEvent.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())