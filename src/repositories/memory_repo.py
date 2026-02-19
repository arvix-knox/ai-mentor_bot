from datetime import datetime, date
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ai_memory import AIMemorySummary, AIInteraction
from src.repositories.base import BaseRepository


class MemoryRepository(BaseRepository):
    model = AIMemorySummary

    async def get_active_summary(
        self, user_id: int, summary_type: str
    ) -> AIMemorySummary | None:
        stmt = (
            select(AIMemorySummary)
            .where(
                and_(
                    AIMemorySummary.user_id == user_id,
                    AIMemorySummary.summary_type == summary_type,
                    AIMemorySummary.is_active == True,
                )
            )
            .order_by(AIMemorySummary.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_summary(
        self,
        user_id: int,
        summary_type: str,
        content: str,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> AIMemorySummary:
        summary = AIMemorySummary(
            user_id=user_id,
            summary_type=summary_type,
            content=content,
            token_count=len(content) // 4,
            period_start=period_start,
            period_end=period_end,
        )
        self.session.add(summary)
        await self.session.flush()
        return summary

    async def deactivate_old_summaries(
        self, user_id: int, summary_type: str, keep_last: int = 4
    ):
        active_stmt = (
            select(AIMemorySummary.id)
            .where(
                and_(
                    AIMemorySummary.user_id == user_id,
                    AIMemorySummary.summary_type == summary_type,
                    AIMemorySummary.is_active == True,
                )
            )
            .order_by(AIMemorySummary.created_at.desc())
            .offset(keep_last)
        )
        result = await self.session.execute(active_stmt)
        old_ids = [row[0] for row in result.all()]

        if old_ids:
            stmt = (
                update(AIMemorySummary)
                .where(AIMemorySummary.id.in_(old_ids))
                .values(is_active=False)
            )
            await self.session.execute(stmt)

    async def create_interaction(
        self,
        user_id: int,
        user_message: str,
        ai_response: str,
        ai_mode: str,
        response_time_ms: int | None = None,
    ) -> AIInteraction:
        interaction = AIInteraction(
            user_id=user_id,
            user_message=user_message,
            ai_response=ai_response,
            ai_mode=ai_mode,
            response_time_ms=response_time_ms,
        )
        self.session.add(interaction)
        await self.session.flush()
        return interaction

    async def get_recent_interactions(
        self, user_id: int, limit: int = 3
    ) -> list[AIInteraction]:
        stmt = (
            select(AIInteraction)
            .where(AIInteraction.user_id == user_id)
            .order_by(AIInteraction.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(reversed(result.scalars().all()))

    async def get_interactions_since(
        self, user_id: int, since: datetime
    ) -> list[AIInteraction]:
        stmt = (
            select(AIInteraction)
            .where(
                and_(
                    AIInteraction.user_id == user_id,
                    AIInteraction.created_at >= since,
                )
            )
            .order_by(AIInteraction.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_interactions_before(
        self, user_id: int, before: datetime
    ):
        stmt = (
            select(AIInteraction)
            .where(
                and_(
                    AIInteraction.user_id == user_id,
                    AIInteraction.created_at < before,
                )
            )
        )
        result = await self.session.execute(stmt)
        for interaction in result.scalars().all():
            await self.session.delete(interaction)
        await self.session.flush()