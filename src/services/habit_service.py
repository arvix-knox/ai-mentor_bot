from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.habit_repo import HabitRepository
from src.services.gamification_service import GamificationService


STREAK_MILESTONES = {7: 50, 14: 100, 30: 250, 60: 500, 100: 1000}


class HabitService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.habit_repo = HabitRepository(session)
        self.gamification = GamificationService(session)

    async def create_habit(
        self,
        user_id: int,
        name: str,
        emoji: str = "✅",
        description: str | None = None,
    ) -> dict:
        habit = await self.habit_repo.create(
            user_id=user_id,
            name=name,
            emoji=emoji,
            description=description,
        )
        return {
            "habit_id": habit.id,
            "name": habit.name,
            "emoji": habit.emoji,
        }

    async def log_completion(
        self, user_id: int, habit_id: int, log_date: date | None = None
    ) -> dict:
        log_date = log_date or date.today()
        habit = await self.habit_repo.get_by_id(habit_id)

        if not habit:
            return {"error": "Habit not found"}

        if habit.user_id != user_id:
            return {"error": "Not your habit"}

        existing = await self.habit_repo.get_log(habit_id, log_date)
        if existing and existing.completed:
            return {"already_logged": True, "streak": habit.current_streak}

        await self.habit_repo.create_log(
            habit_id=habit_id,
            user_id=user_id,
            log_date=log_date,
            completed=True,
        )

        new_streak = await self._calculate_streak(habit_id, log_date)
        best_streak = max(habit.best_streak, new_streak)
        total_completions = habit.total_completions + 1

        await self.habit_repo.update(
            habit_id,
            current_streak=new_streak,
            best_streak=best_streak,
            total_completions=total_completions,
        )

        xp_earned = habit.xp_per_completion
        await self.gamification.award_xp(
            user_id, "habit_completed", xp_earned,
            source_type="habit", source_id=habit_id,
        )

        milestone = None
        if new_streak in STREAK_MILESTONES:
            milestone = new_streak
            bonus = STREAK_MILESTONES[new_streak]
            await self.gamification.award_xp(
                user_id,
                f"habit_streak_{new_streak}",
                bonus,
                source_type="habit",
                source_id=habit_id,
                description=f"🔥 {new_streak}-day streak on {habit.name}!",
            )
            xp_earned += bonus

        return {
            "streak": new_streak,
            "best_streak": best_streak,
            "xp_earned": xp_earned,
            "streak_milestone": milestone,
            "total_completions": total_completions,
        }

    async def _calculate_streak(self, habit_id: int, current_date: date) -> int:
        habit = await self.habit_repo.get_by_id(habit_id)
        streak = 0
        check_date = current_date

        while True:
            day_bit = 1 << check_date.weekday()

            if habit.schedule_mask & day_bit:
                log = await self.habit_repo.get_log(habit_id, check_date)
                if log and (log.completed or log.is_freeze):
                    streak += 1
                elif check_date < current_date:
                    break
                else:
                    streak += 1

            check_date -= timedelta(days=1)

            if (current_date - check_date).days > 365:
                break

        return streak

    async def check_missed_habits(self, user_id: int):
        yesterday = date.today() - timedelta(days=1)
        habits = await self.habit_repo.get_active_habits(user_id)

        for habit in habits:
            day_bit = 1 << yesterday.weekday()
            if not (habit.schedule_mask & day_bit):
                continue

            log = await self.habit_repo.get_log(habit.id, yesterday)
            if not log:
                await self.habit_repo.update(habit.id, current_streak=0)
                await self.gamification.apply_penalty(
                    user_id, "habit_missed",
                    description=f"Missed habit: {habit.name}",
                )

    async def get_user_habits(self, user_id: int) -> list:
        return await self.habit_repo.get_active_habits(user_id)

    async def get_weekly_performance(self, user_id: int) -> dict:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        habits = await self.habit_repo.get_active_habits(user_id)

        total_possible = 0
        total_completed = 0
        habit_details = []

        for habit in habits:
            possible = 0
            completed = 0

            for day_offset in range(7):
                check_date = week_start + timedelta(days=day_offset)
                if check_date > today:
                    break

                day_bit = 1 << check_date.weekday()
                if habit.schedule_mask & day_bit:
                    possible += 1
                    log = await self.habit_repo.get_log(habit.id, check_date)
                    if log and log.completed:
                        completed += 1

            total_possible += possible
            total_completed += completed

            habit_details.append({
                "name": habit.name,
                "emoji": habit.emoji,
                "completed": completed,
                "possible": possible,
                "rate": completed / possible if possible > 0 else 0,
                "streak": habit.current_streak,
                "best_streak": habit.best_streak,
            })

        overall_rate = total_completed / total_possible if total_possible > 0 else 0

        return {
            "overall_rate": overall_rate,
            "total_completed": total_completed,
            "total_possible": total_possible,
            "habits": habit_details,
            "best_streak": max((h["streak"] for h in habit_details), default=0),
        }