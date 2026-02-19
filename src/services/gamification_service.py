import math
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.xp_repo import XPRepository
from src.repositories.user_repo import UserRepository

XP_AWARDS = {
    "task_created": 5,
    "task_completed_low": 10,
    "task_completed_medium": 20,
    "task_completed_high": 35,
    "task_completed_critical": 50,
    "task_completed_before_deadline": 15,
    "habit_completed": 15,
    "habit_streak_7": 50,
    "habit_streak_14": 100,
    "habit_streak_30": 250,
    "habit_streak_60": 500,
    "habit_streak_100": 1000,
    "journal_entry": 10,
    "journal_entry_long": 20,
    "ai_session": 5,
    "weekly_review_read": 10,
    "profile_setup": 25,
}

XP_PENALTIES = {
    "habit_missed": -10,
    "task_overdue": -5,
    "inactivity_day": -3,
}


class GamificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.xp_repo = XPRepository(session)
        self.user_repo = UserRepository(session)

    @staticmethod
    def xp_for_level(level: int) -> int:
        if level <= 1:
            return 0
        return int(100 * math.pow(level, 1.5))

    @staticmethod
    def level_from_xp(total_xp: int) -> int:
        level = 1
        while GamificationService.xp_for_level(level + 1) <= total_xp:
            level += 1
        return level

    @staticmethod
    def xp_progress(total_xp: int) -> tuple[int, int, float]:
        level = GamificationService.level_from_xp(total_xp)
        current_threshold = GamificationService.xp_for_level(level)
        next_threshold = GamificationService.xp_for_level(level + 1)

        xp_in_level = total_xp - current_threshold
        xp_needed = next_threshold - current_threshold
        progress = xp_in_level / xp_needed if xp_needed > 0 else 0

        return level, xp_needed - xp_in_level, progress

    @staticmethod
    def format_level_progress(total_xp: int) -> str:
        level, xp_to_next, progress = GamificationService.xp_progress(total_xp)
        bar_length = 20
        filled = int(progress * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        return (
            f"⭐ Level {level}\n"
            f"[{bar}] {progress:.0%}\n"
            f"XP: {total_xp} | До level {level + 1}: {xp_to_next} XP"
        )

    async def award_xp(
        self,
        user_id: int,
        event_type: str,
        xp_amount: int | None = None,
        source_type: str | None = None,
        source_id: int | None = None,
        description: str | None = None,
    ) -> tuple[int, bool]:
        if xp_amount is None:
            xp_amount = XP_AWARDS.get(event_type, 0)

        if xp_amount == 0:
            user = await self.user_repo.get_by_id(user_id)
            return user.total_xp_earned, False

        await self.xp_repo.create_event(
            user_id=user_id,
            event_type=event_type,
            xp_amount=xp_amount,
            source_type=source_type,
            source_id=source_id,
            description=description,
        )

        user = await self.user_repo.get_by_id(user_id)
        old_level = user.level

        new_xp = max(0, user.xp + xp_amount)
        new_total = user.total_xp_earned + max(0, xp_amount)
        new_level = self.level_from_xp(new_total)

        await self.user_repo.update(
            user_id, xp=new_xp, total_xp_earned=new_total, level=new_level
        )

        leveled_up = new_level > old_level
        return new_total, leveled_up

    async def apply_penalty(
        self, user_id: int, penalty_type: str, description: str | None = None
    ):
        xp_amount = XP_PENALTIES.get(penalty_type, -5)
        await self.award_xp(user_id, penalty_type, xp_amount, description=description)

    async def calculate_discipline_score(self, user_id: int, days: int = 7) -> float:
        since = datetime.utcnow() - timedelta(days=days)

        from src.repositories.habit_repo import HabitRepository
        habit_repo = HabitRepository(self.session)
        habit_rate = await habit_repo.get_completion_rate(user_id, since)
        habit_score = habit_rate * 100

        from src.repositories.task_repo import TaskRepository
        task_repo = TaskRepository(self.session)
        task_rate = await task_repo.get_completion_rate(user_id, since)
        task_score = task_rate * 100

        active_days = await self.xp_repo.get_active_days_count(user_id, since)
        consistency_score = (active_days / days) * 100

        discipline = habit_score * 0.40 + task_score * 0.30 + consistency_score * 0.30

        user = await self.user_repo.get_by_id(user_id)
        smoothed = user.discipline_score * 0.3 + discipline * 0.7

        await self.user_repo.update(user_id, discipline_score=round(smoothed, 1))
        return smoothed

    async def calculate_growth_score(self, user_id: int, days: int = 7) -> float:
        since = datetime.utcnow() - timedelta(days=days)

        from src.repositories.journal_repo import JournalRepository
        journal_repo = JournalRepository(self.session)
        journal_count = await journal_repo.count_entries(user_id, since)
        journal_score = min(100, journal_count * 20)

        ai_count = await self.xp_repo.count_events(user_id, "ai_session", since)
        ai_score = min(100, ai_count * 15)

        active_days = await self.xp_repo.get_active_days_count(user_id, since)
        activity_score = min(100, active_days * 15)

        growth = journal_score * 0.40 + ai_score * 0.30 + activity_score * 0.30

        user = await self.user_repo.get_by_id(user_id)
        smoothed = user.growth_score * 0.3 + growth * 0.7

        await self.user_repo.update(user_id, growth_score=round(smoothed, 1))
        return smoothed