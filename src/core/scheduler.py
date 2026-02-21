from datetime import datetime, date
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
import logging

from src.core.database import async_session_factory
from src.models.user import User
from src.repositories.task_repo import TaskRepository
from src.repositories.habit_repo import HabitRepository

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.sent_cache: set[str] = set()

    def start(self):
        if self.scheduler.running:
            return
        self.scheduler.add_job(
            self.dispatch_tick,
            "interval",
            minutes=1,
            id="dispatch_notifications",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.start()

    async def dispatch_tick(self):
        from src.bot.loader import bot

        if len(self.sent_cache) > 20000:
            self.sent_cache.clear()

        try:
            async with async_session_factory() as session:
                users = (
                    await session.execute(select(User).where(User.is_active == True))
                ).scalars().all()
                task_repo = TaskRepository(session)
                habit_repo = HabitRepository(session)

                for user in users:
                    timezone = user.timezone or "Europe/Moscow"
                    try:
                        tz = ZoneInfo(timezone)
                    except Exception:
                        tz = ZoneInfo("Europe/Moscow")
                    local_now = datetime.now(tz)
                    hhmm = local_now.strftime("%H:%M")
                    today = local_now.date()
                    weekday = local_now.weekday()
                    settings_data = user.get_settings()
                    notif = settings_data.get("notifications", {})

                    if notif.get("task_remind_default", True):
                        tasks = await task_repo.get_reminder_tasks(hhmm, today)
                        for task in tasks:
                            if task.user_id != user.id:
                                continue
                            cache_key = f"task:{user.id}:{task.id}:{today.isoformat()}:{hhmm}"
                            if cache_key in self.sent_cache:
                                continue
                            self.sent_cache.add(cache_key)
                            text = task.remind_text or notif.get("remind_text_template", "🔔 Пора: {name}").format(name=task.title)
                            try:
                                await bot.send_message(user.telegram_id, text)
                            except Exception:
                                continue

                    if notif.get("habit_remind_default", True):
                        habits = await habit_repo.get_reminder_habits(hhmm, weekday)
                        for habit in habits:
                            if habit.user_id != user.id:
                                continue
                            cache_key = f"habit:{user.id}:{habit.id}:{today.isoformat()}:{hhmm}"
                            if cache_key in self.sent_cache:
                                continue
                            self.sent_cache.add(cache_key)
                            text = habit.remind_text or f"🔄 Пора выполнить привычку: {habit.emoji} {habit.name}"
                            try:
                                await bot.send_message(user.telegram_id, text)
                            except Exception:
                                continue

                    if notif.get("morning", True) and notif.get("morning_time") == hhmm:
                        cache_key = f"morning:{user.id}:{today.isoformat()}:{hhmm}"
                        if cache_key not in self.sent_cache:
                            self.sent_cache.add(cache_key)
                            try:
                                await bot.send_message(
                                    user.telegram_id,
                                    "🌅 Доброе утро! Проверь задачи и начни с самой важной.",
                                )
                            except Exception:
                                continue

                    if notif.get("evening", True) and notif.get("evening_time") == hhmm:
                        cache_key = f"evening:{user.id}:{today.isoformat()}:{hhmm}"
                        if cache_key not in self.sent_cache:
                            self.sent_cache.add(cache_key)
                            try:
                                await bot.send_message(
                                    user.telegram_id,
                                    "🌙 Вечерний чек-ин: закрой минимум 1 задачу и отметь привычки.",
                                )
                            except Exception:
                                continue
        except Exception as e:
            logger.warning("Reminder tick skipped (db/network): %s", e)


reminder_scheduler = ReminderScheduler()
