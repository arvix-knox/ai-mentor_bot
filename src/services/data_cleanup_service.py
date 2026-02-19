from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.user_repo import UserRepository
from src.models.ai_memory import AIInteraction, AIMemorySummary
from src.models.journal import JournalEntry
from src.models.gamification import XPEvent, UserAchievement


PERIOD_TO_DELTA = {
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


class DataCleanupService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def delete_profile(self, user_id: int) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"error": "Профиль не найден"}
        await self.user_repo.delete(user_id)
        return {"deleted": True}

    async def cleanup_history(self, user_id: int, period: str) -> dict:
        period = period.lower().strip()
        if period == "all":
            cutoff = None
        else:
            delta = PERIOD_TO_DELTA.get(period)
            if not delta:
                return {"error": "Неверный период"}
            cutoff = datetime.utcnow() - delta

        deleted_ai = await self._delete_rows(AIInteraction, user_id, cutoff, "created_at")
        deleted_summaries = await self._delete_rows(AIMemorySummary, user_id, cutoff, "created_at")
        deleted_journal = await self._delete_rows(JournalEntry, user_id, cutoff, "created_at")
        deleted_xp = await self._delete_rows(XPEvent, user_id, cutoff, "created_at")
        deleted_ach = await self._delete_rows(UserAchievement, user_id, cutoff, "unlocked_at")

        return {
            "deleted_ai": deleted_ai,
            "deleted_summaries": deleted_summaries,
            "deleted_journal": deleted_journal,
            "deleted_xp_events": deleted_xp,
            "deleted_achievements": deleted_ach,
            "period": period,
        }

    async def _delete_rows(
        self,
        model,
        user_id: int,
        cutoff: datetime | None,
        time_field: str,
    ) -> int:
        filters = [getattr(model, "user_id") == user_id]
        if cutoff is not None:
            filters.append(getattr(model, time_field) >= cutoff)
        stmt = select(model).where(and_(*filters))
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        for row in rows:
            await self.session.delete(row)
        await self.session.flush()
        return len(rows)
