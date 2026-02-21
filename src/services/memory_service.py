import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.memory_repo import MemoryRepository
from src.repositories.task_repo import TaskRepository
from src.repositories.habit_repo import HabitRepository
from src.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memory_repo = MemoryRepository(session)
        self.task_repo = TaskRepository(session)
        self.habit_repo = HabitRepository(session)
        self.user_repo = UserRepository(session)

    async def build_context(self, user_id: int) -> str:
        profile_block = await self._build_profile_block(user_id)
        weekly_block = await self._build_weekly_block(user_id)
        session_block = await self._build_session_block(user_id)

        context = (
            f"=== USER PROFILE ===\n{profile_block}\n\n"
            f"=== CURRENT WEEK ===\n{weekly_block}\n\n"
            f"=== RECENT CONVERSATION ===\n{session_block}"
        )

        return self._truncate_context(context, max_tokens=900)

    async def _build_profile_block(self, user_id: int) -> str:
        user = await self.user_repo.get_by_id(user_id)

        summary = await self.memory_repo.get_active_summary(user_id, "profile_summary")
        if summary:
            return summary.content

        tech_stack = []
        goals = []
        try:
            if user.tech_stack:
                tech_stack = json.loads(user.tech_stack)
            if user.goals:
                goals = json.loads(user.goals)
        except (json.JSONDecodeError, TypeError):
            pass

        tech_str = ", ".join(tech_stack) if tech_stack else "Not set"
        goals_str = ", ".join(goals) if goals else "Not set"

        return (
            f"Name: {user.get_display_name()}\n"
            f"Level: {user.level} (XP: {user.xp})\n"
            f"Tech Stack: {tech_str}\n"
            f"Goals: {goals_str}\n"
            f"Discipline Score: {user.discipline_score:.0f}/100\n"
            f"Growth Score: {user.growth_score:.0f}/100\n"
            f"AI Mode: {user.ai_mode}"
        )

    async def _build_weekly_block(self, user_id: int) -> str:
        tasks = await self.task_repo.get_active_tasks(user_id, limit=5)
        if tasks:
            tasks_text = "\n".join(
                f"- [{t.priority}] {t.title}"
                + (f" (due: {t.deadline})" if t.deadline else "")
                for t in tasks
            )
        else:
            tasks_text = "No active tasks"

        habits = await self.habit_repo.get_active_habits(user_id)
        if habits:
            habits_text = "\n".join(
                f"- {h.emoji} {h.name}: streak {h.current_streak}d"
                for h in habits
            )
        else:
            habits_text = "No habits tracked"

        weekly_summary = await self.memory_repo.get_active_summary(user_id, "weekly_summary")
        summary_text = weekly_summary.content if weekly_summary else "No weekly summary yet"

        return (
            f"Active Tasks:\n{tasks_text}\n\n"
            f"Habits:\n{habits_text}\n\n"
            f"Last Week Summary: {summary_text}"
        )

    async def _build_session_block(self, user_id: int) -> str:
        interactions = await self.memory_repo.get_recent_interactions(user_id, limit=3)
        if not interactions:
            return "No previous messages in this session."

        lines = []
        for inter in interactions:
            user_msg = inter.user_message[:150]
            ai_msg = inter.ai_response[:150]
            lines.append(f"User: {user_msg}")
            lines.append(f"AI: {ai_msg}")

        return "\n".join(lines)

    def _truncate_context(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n[...context truncated...]"

    async def compress_memory(self, user_id: int):
        week_ago = datetime.utcnow() - timedelta(days=7)

        interactions = await self.memory_repo.get_interactions_since(user_id, week_ago)
        if not interactions:
            return

        interaction_text = "\n".join(
            f"User: {i.user_message[:100]}\nAI: {i.ai_response[:100]}"
            for i in interactions[-20:]
        )

        from src.services.ai_service import AIService
        ai_svc = AIService(self.session)

        summary = await ai_svc.generate_summary(
            f"Summarize these mentoring interactions in 3-5 bullet points:\n{interaction_text}"
        )

        await self.memory_repo.create_summary(
            user_id=user_id,
            summary_type="weekly_summary",
            content=summary,
            period_start=(datetime.utcnow() - timedelta(days=7)).date(),
            period_end=datetime.utcnow().date(),
        )

        await self.memory_repo.deactivate_old_summaries(
            user_id, "weekly_summary", keep_last=4
        )

        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        await self.memory_repo.delete_interactions_before(user_id, two_weeks_ago)
