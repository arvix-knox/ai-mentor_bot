from datetime import date, datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.habit import Habit, HabitLog
from src.repositories.base import BaseRepository


class HabitRepository(BaseRepository):
    model = Habit

    async def get_active_habits(self, user_id: int) -> list[Habit]:
        stmt = (
            select(Habit)
            .where(
                and_(
                    Habit.user_id == user_id,
                    Habit.is_active == True,
                )
            )
            .order_by(Habit.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_reminder_habits(
        self,
        remind_time: str,
        weekday_index: int,
    ) -> list[Habit]:
        day_bit = 1 << weekday_index
        stmt = (
            select(Habit)
            .where(
                and_(
                    Habit.is_active == True,
                    Habit.remind_enabled == True,
                    Habit.remind_time == remind_time,
                )
            )
            .order_by(Habit.created_at.asc())
        )
        result = await self.session.execute(stmt)
        habits = list(result.scalars().all())
        return [h for h in habits if h.schedule_mask & day_bit]

    async def get_log(self, habit_id: int, log_date: date) -> HabitLog | None:
        stmt = select(HabitLog).where(
            and_(
                HabitLog.habit_id == habit_id,
                HabitLog.log_date == log_date,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_log(
        self,
        habit_id: int,
        user_id: int,
        log_date: date,
        completed: bool = True,
        is_freeze: bool = False,
    ) -> HabitLog:
        log = HabitLog(
            habit_id=habit_id,
            user_id=user_id,
            log_date=log_date,
            completed=completed,
            is_freeze=is_freeze,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_logs_range(
        self,
        habit_id: int,
        start_date: date,
        end_date: date,
    ) -> list[HabitLog]:
        stmt = (
            select(HabitLog)
            .where(
                and_(
                    HabitLog.habit_id == habit_id,
                    HabitLog.log_date >= start_date,
                    HabitLog.log_date <= end_date,
                )
            )
            .order_by(HabitLog.log_date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_completion_rate(
        self, user_id: int, since: datetime
    ) -> float:
        since_date = since.date() if isinstance(since, datetime) else since

        total_stmt = select(func.count()).where(
            and_(
                HabitLog.user_id == user_id,
                HabitLog.log_date >= since_date,
            )
        )
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar()

        if total == 0:
            return 0.0

        completed_stmt = select(func.count()).where(
            and_(
                HabitLog.user_id == user_id,
                HabitLog.log_date >= since_date,
                HabitLog.completed == True,
            )
        )
        completed_result = await self.session.execute(completed_stmt)
        completed = completed_result.scalar()

        return completed / total
