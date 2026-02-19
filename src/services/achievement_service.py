from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.gamification import Achievement
from src.models.task import Task
from src.models.habit import Habit, HabitLog
from src.models.journal import JournalEntry
from src.models.ai_memory import AIInteraction
from src.models.playlist import Playlist, PlaylistTrack
from src.models.learning import LearningResource
from src.repositories.achievement_repo import AchievementRepository
from src.repositories.user_repo import UserRepository
from src.services.gamification_service import GamificationService


DEFAULT_ACHIEVEMENTS: list[dict] = [
    {
        "code": "task_first_create",
        "name": "Первый шаг",
        "description": "Создать первую задачу",
        "emoji": "🧩",
        "xp_reward": 25,
        "category": "tasks",
        "condition_type": "tasks_created",
        "condition_value": 1,
    },
    {
        "code": "task_complete_10",
        "name": "Доводчик",
        "description": "Выполнить 10 задач",
        "emoji": "✅",
        "xp_reward": 60,
        "category": "tasks",
        "condition_type": "tasks_completed",
        "condition_value": 10,
    },
    {
        "code": "task_complete_50",
        "name": "Машина продуктивности",
        "description": "Выполнить 50 задач",
        "emoji": "🚀",
        "xp_reward": 180,
        "category": "tasks",
        "condition_type": "tasks_completed",
        "condition_value": 50,
    },
    {
        "code": "task_clean_slate",
        "name": "Чистый лист",
        "description": "Закрыть все активные задачи",
        "emoji": "🧹",
        "xp_reward": 80,
        "category": "tasks",
        "condition_type": "all_active_tasks_done",
        "condition_value": 1,
    },
    {
        "code": "habit_first",
        "name": "Ритм",
        "description": "Создать первую привычку",
        "emoji": "🔄",
        "xp_reward": 25,
        "category": "habits",
        "condition_type": "habits_created",
        "condition_value": 1,
    },
    {
        "code": "habit_complete_30",
        "name": "Дисциплина",
        "description": "30 отметок привычек",
        "emoji": "🔥",
        "xp_reward": 120,
        "category": "habits",
        "condition_type": "habit_logs_completed",
        "condition_value": 30,
    },
    {
        "code": "journal_first",
        "name": "Рефлексия",
        "description": "Сделать первую запись в журнале",
        "emoji": "📝",
        "xp_reward": 25,
        "category": "journal",
        "condition_type": "journal_entries",
        "condition_value": 1,
    },
    {
        "code": "journal_20",
        "name": "Хроникер",
        "description": "Сделать 20 записей в журнале",
        "emoji": "📚",
        "xp_reward": 120,
        "category": "journal",
        "condition_type": "journal_entries",
        "condition_value": 20,
    },
    {
        "code": "ai_10",
        "name": "Диалог с наставником",
        "description": "10 сессий с AI",
        "emoji": "🤖",
        "xp_reward": 70,
        "category": "ai",
        "condition_type": "ai_sessions",
        "condition_value": 10,
    },
    {
        "code": "ai_50",
        "name": "Плотная работа с AI",
        "description": "50 сессий с AI",
        "emoji": "🧠",
        "xp_reward": 200,
        "category": "ai",
        "condition_type": "ai_sessions",
        "condition_value": 50,
    },
    {
        "code": "level_5",
        "name": "Уровень 5",
        "description": "Достичь 5 уровня",
        "emoji": "⭐",
        "xp_reward": 100,
        "category": "progress",
        "condition_type": "level",
        "condition_value": 5,
    },
    {
        "code": "level_10",
        "name": "Уровень 10",
        "description": "Достичь 10 уровня",
        "emoji": "🌟",
        "xp_reward": 250,
        "category": "progress",
        "condition_type": "level",
        "condition_value": 10,
    },
    {
        "code": "resource_5",
        "name": "Любознательный",
        "description": "Пройти 5 учебных материалов",
        "emoji": "🎓",
        "xp_reward": 90,
        "category": "learning",
        "condition_type": "resources_completed",
        "condition_value": 5,
    },
    {
        "code": "resource_20",
        "name": "Исследователь",
        "description": "Пройти 20 учебных материалов",
        "emoji": "🧭",
        "xp_reward": 220,
        "category": "learning",
        "condition_type": "resources_completed",
        "condition_value": 20,
    },
    {
        "code": "playlist_first",
        "name": "Саундтрек дня",
        "description": "Создать первый плейлист",
        "emoji": "🎵",
        "xp_reward": 30,
        "category": "media",
        "condition_type": "playlists_created",
        "condition_value": 1,
    },
    {
        "code": "playlist_20_tracks",
        "name": "Музыкальный архив",
        "description": "Собрать 20 треков в плейлистах",
        "emoji": "🎧",
        "xp_reward": 120,
        "category": "media",
        "condition_type": "playlist_tracks",
        "condition_value": 20,
    },
    {
        "code": "active_week",
        "name": "Без пропусков",
        "description": "Активность 7 дней подряд",
        "emoji": "📆",
        "xp_reward": 110,
        "category": "consistency",
        "condition_type": "active_days_7",
        "condition_value": 7,
    },
    {
        "code": "profile_complete",
        "name": "Профиль настроен",
        "description": "Заполнить имя, стек и цели",
        "emoji": "👤",
        "xp_reward": 50,
        "category": "profile",
        "condition_type": "profile_filled",
        "condition_value": 1,
    },
    {
        "code": "goal_executor",
        "name": "Целеустремленный",
        "description": "Выполнить 100 задач и привычек суммарно",
        "emoji": "🏁",
        "xp_reward": 300,
        "category": "mastery",
        "condition_type": "total_productive_actions",
        "condition_value": 100,
    },
]


class AchievementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AchievementRepository(session)
        self.user_repo = UserRepository(session)
        self.gamification = GamificationService(session)

    async def ensure_catalog(self) -> None:
        for payload in DEFAULT_ACHIEVEMENTS:
            await self.repo.get_or_create_achievement(payload)

    async def evaluate(self, user_id: int) -> list[Achievement]:
        await self.ensure_catalog()
        unlocked: list[Achievement] = []
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return unlocked

        achievements = await self.repo.get_all(limit=300)
        stats = await self._collect_stats(user_id, user.level)

        for ach in achievements:
            if await self.repo.user_has_achievement(user_id, ach.id):
                continue
            if self._matches_condition(ach, stats):
                await self.repo.unlock(user_id, ach.id)
                unlocked.append(ach)
                await self.gamification.award_xp(
                    user_id,
                    event_type=f"achievement:{ach.code}",
                    xp_amount=ach.xp_reward,
                    source_type="achievement",
                    source_id=ach.id,
                    description=f"🏆 {ach.name}",
                )

        return unlocked

    async def get_user_achievements(self, user_id: int) -> list[Achievement]:
        rows = await self.repo.list_user_achievements(user_id)
        items: list[Achievement] = []
        for row in rows:
            if row.achievement:
                items.append(row.achievement)
        return items

    async def _collect_stats(self, user_id: int, level: int) -> dict:
        tasks_created = await self._count_rows(Task, user_id=user_id)
        tasks_completed = await self._count_rows(Task, user_id=user_id, status="done")
        active_tasks = await self._count_rows(Task, user_id=user_id, status_in=["todo", "in_progress"])

        habits_created = await self._count_rows(Habit, user_id=user_id)
        habit_logs_completed = await self._count_rows(HabitLog, user_id=user_id, completed=True)
        journal_entries = await self._count_rows(JournalEntry, user_id=user_id)
        ai_sessions = await self._count_rows(AIInteraction, user_id=user_id)
        playlists_created = await self._count_rows(Playlist, user_id=user_id)
        playlist_tracks = await self._count_tracks(user_id)
        resources_completed = await self._count_rows(LearningResource, user_id=user_id, is_completed=True)
        active_days_7 = await self._active_days_last_week(user_id)

        user = await self.user_repo.get_by_id(user_id)
        profile_filled = int(bool(user.get_display_name() and user.tech_stack and user.goals))

        return {
            "tasks_created": tasks_created,
            "tasks_completed": tasks_completed,
            "all_active_tasks_done": int(active_tasks == 0 and tasks_completed > 0),
            "habits_created": habits_created,
            "habit_logs_completed": habit_logs_completed,
            "journal_entries": journal_entries,
            "ai_sessions": ai_sessions,
            "level": level,
            "resources_completed": resources_completed,
            "playlists_created": playlists_created,
            "playlist_tracks": playlist_tracks,
            "active_days_7": active_days_7,
            "profile_filled": profile_filled,
            "total_productive_actions": tasks_completed + habit_logs_completed,
        }

    async def _count_rows(self, model, **filters) -> int:
        stmt = select(func.count()).select_from(model)

        status_in = filters.pop("status_in", None)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        if status_in:
            stmt = stmt.where(getattr(model, "status").in_(status_in))

        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def _count_tracks(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(PlaylistTrack)
            .join(Playlist, PlaylistTrack.playlist_id == Playlist.id)
            .where(Playlist.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def _active_days_last_week(self, user_id: int) -> int:
        since = datetime.utcnow() - timedelta(days=7)
        stmt = (
            select(func.count(func.distinct(func.date(AIInteraction.created_at))))
            .where(
                and_(
                    AIInteraction.user_id == user_id,
                    AIInteraction.created_at >= since,
                )
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    @staticmethod
    def _matches_condition(achievement: Achievement, stats: dict) -> bool:
        current = stats.get(achievement.condition_type, 0)
        return int(current) >= int(achievement.condition_value)
