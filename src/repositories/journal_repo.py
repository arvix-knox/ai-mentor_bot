from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.journal import JournalEntry
from src.repositories.base import BaseRepository


class JournalRepository(BaseRepository):
    model = JournalEntry

    async def get_recent(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> list[JournalEntry]:
        stmt = (
            select(JournalEntry)
            .where(JournalEntry.user_id == user_id)
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_tags(
        self,
        user_id: int,
        tags: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> list[JournalEntry]:
        stmt = (
            select(JournalEntry)
            .where(
                and_(
                    JournalEntry.user_id == user_id,
                    JournalEntry.tags.overlap(tags),
                )
            )
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def full_text_search(
        self,
        user_id: int,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JournalEntry]:
        ts_query = func.plainto_tsquery("russian", query)
        stmt = (
            select(JournalEntry)
            .where(
                and_(
                    JournalEntry.user_id == user_id,
                    JournalEntry.search_vector.op("@@")(ts_query),
                )
            )
            .order_by(
                func.ts_rank(JournalEntry.search_vector, ts_query).desc()
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_shared_tags(
        self,
        user_id: int,
        tags: list[str],
        exclude_id: int,
        limit: int = 5,
    ) -> list[JournalEntry]:
        stmt = (
            select(JournalEntry)
            .where(
                and_(
                    JournalEntry.user_id == user_id,
                    JournalEntry.id != exclude_id,
                    JournalEntry.tags.overlap(tags),
                )
            )
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_entries(self, user_id: int, since: datetime) -> int:
        stmt = select(func.count()).where(
            and_(
                JournalEntry.user_id == user_id,
                JournalEntry.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()