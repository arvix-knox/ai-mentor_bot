from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.gamification import Achievement, UserAchievement
from src.repositories.base import BaseRepository


class AchievementRepository(BaseRepository):
    model = Achievement

    async def get_by_code(self, code: str) -> Achievement | None:
        stmt = select(Achievement).where(Achievement.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_achievement(self, payload: dict) -> Achievement:
        existing = await self.get_by_code(payload["code"])
        if existing:
            return existing
        ach = Achievement(**payload)
        self.session.add(ach)
        await self.session.flush()
        await self.session.refresh(ach)
        return ach

    async def list_user_achievements(self, user_id: int) -> list[UserAchievement]:
        stmt = (
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def user_has_achievement(self, user_id: int, achievement_id: int) -> bool:
        stmt = select(UserAchievement.id).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def unlock(self, user_id: int, achievement_id: int) -> UserAchievement:
        rec = UserAchievement(user_id=user_id, achievement_id=achievement_id)
        self.session.add(rec)
        await self.session.flush()
        await self.session.refresh(rec)
        return rec

    async def count_user_achievements(self, user_id: int) -> int:
        stmt = select(func.count()).where(UserAchievement.user_id == user_id)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
