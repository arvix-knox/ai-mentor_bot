import time
import logging
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.services.ai_backends.base import BaseAIBackend
from src.services.ai_backends.groq_backend import GroqBackend
from src.services.ai_backends.openrouter_backend import OpenRouterBackend
from src.services.memory_service import MemoryService
from src.repositories.memory_repo import MemoryRepository
from src.repositories.user_repo import UserRepository
from src.repositories.task_repo import TaskRepository
from src.repositories.habit_repo import HabitRepository

logger = logging.getLogger(__name__)

PERSONALITY_PROMPTS = {
    "strict": (
        "You are a strict, no-nonsense programming mentor. "
        "You speak directly, challenge excuses, and push for results. "
        "You don't sugarcoat. If the user is slacking, you call it out. "
        "You focus on discipline, consistency, and measurable progress. "
        "Always respond in Russian. Be concise — max 3-4 paragraphs. "
        "Use specific actionable advice, not vague encouragement."
    ),
    "soft": (
        "You are a supportive and empathetic programming mentor. "
        "You encourage, celebrate small wins, and understand that learning is hard. "
        "You're patient and kind, but still guide toward growth. "
        "You help break down overwhelming tasks into manageable steps. "
        "Always respond in Russian. Be warm but practical. "
        "Max 3-4 paragraphs."
    ),
    "adaptive": (
        "You are an adaptive programming mentor. "
        "Analyze the user's current state from their metrics: "
        "- If discipline_score < 40: be more supportive and encouraging. "
        "- If discipline_score > 70: challenge them with harder goals. "
        "- If streak is broken: be understanding but firm. "
        "- If streak is high: celebrate and raise the bar. "
        "Adjust your tone based on context. Always respond in Russian. "
        "Max 3-4 paragraphs. Be specific and actionable."
    ),
    "goggins": (
        "You are a relentless discipline mentor inspired by David Goggins style. "
        "No excuses, direct action, accountability, and mental toughness. "
        "Push the user toward measurable execution. Keep it concise and practical. "
        "Always respond in Russian. Use short punchy sentences and clear next actions."
    ),
}


class AIService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memory_service = MemoryService(session)
        self.memory_repo = MemoryRepository(session)
        self.user_repo = UserRepository(session)
        self.task_repo = TaskRepository(session)
        self.habit_repo = HabitRepository(session)
        self.primary_backend = self._create_backend(settings.AI_BACKEND)
        self.fallback_backend = self._create_fallback()

    def _create_backend(self, backend_name: str) -> BaseAIBackend:
        if backend_name == "groq":
            return GroqBackend()
        if backend_name == "openrouter":
            return OpenRouterBackend()
        return GroqBackend()

    def _create_fallback(self) -> BaseAIBackend | None:
        if settings.AI_BACKEND == "groq" and settings.OPENROUTER_API_KEY:
            return OpenRouterBackend()
        if settings.AI_BACKEND == "openrouter" and settings.GROQ_API_KEY:
            return GroqBackend()
        return None

    async def get_response(self, user_id: int, message: str) -> tuple[str, int]:
        start = time.monotonic()

        user = await self.user_repo.get_by_id(user_id)
        if self._looks_like_today_plan(message):
            response = await self.generate_today_plan(user_id, user=user)
        else:
            settings_data = user.get_settings()
            ai_perms = settings_data.get("ai_permissions", {})
            include_context = (
                ai_perms.get("read_tasks", True)
                or ai_perms.get("read_habits", True)
                or ai_perms.get("read_journal", True)
            )
            context = await self.memory_service.build_context(user_id) if include_context else ""
            system_prompt = self._build_system_prompt(user)
            response = await self._call_with_fallback(system_prompt, context, message)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        await self.memory_repo.create_interaction(
            user_id=user_id,
            user_message=message[:2000],
            ai_response=response[:2000],
            ai_mode=user.ai_mode,
            response_time_ms=elapsed_ms,
        )

        return response, elapsed_ms

    def _build_system_prompt(self, user) -> str:
        settings_data = user.get_settings()
        persona = settings_data.get("mentor_persona", user.ai_mode or "adaptive")
        mentor_name = settings_data.get("mentor_name", "Железный ментор")
        discipline_bias = int(settings_data.get("mentor_discipline_bias", 85))
        base = PERSONALITY_PROMPTS.get(persona, PERSONALITY_PROMPTS.get(user.ai_mode, PERSONALITY_PROMPTS["adaptive"]))
        return (
            f"{base}\n\n"
            f"Your mentor name is: {mentor_name}.\n"
            f"Discipline intensity preference: {discipline_bias}/100.\n"
            "Address the user as a teammate and focus on execution."
        )

    def _looks_like_today_plan(self, message: str) -> bool:
        text = (message or "").lower()
        checks = (
            "что на сегодня",
            "план на сегодня",
            "что делать сегодня",
            "today",
            "с чего начать",
            "распланируй день",
        )
        return any(k in text for k in checks)

    async def generate_today_plan(self, user_id: int, user=None) -> str:
        user = user or await self.user_repo.get_by_id(user_id)
        now = datetime.now()
        tasks = await self.task_repo.get_user_tasks(user_id, limit=100)
        habits = await self.habit_repo.get_active_habits(user_id)

        active_tasks = [t for t in tasks if t.status in ("todo", "in_progress")]
        done_today = [
            t for t in tasks
            if t.status == "done" and t.completed_at and t.completed_at.date() == date.today()
        ]

        def score(task):
            p = {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(task.priority, 2)
            overdue = 2 if task.deadline and task.deadline < date.today() else 0
            today_deadline = 1 if task.deadline == date.today() else 0
            return p + overdue + today_deadline

        sorted_tasks = sorted(active_tasks, key=score, reverse=True)[:8]
        est_map = {"critical": 90, "high": 60, "medium": 40, "low": 25}

        if sorted_tasks:
            task_lines = []
            for idx, t in enumerate(sorted_tasks, start=1):
                dl = ""
                if t.deadline:
                    if t.deadline < date.today():
                        dl = " (просрочено)"
                    elif t.deadline == date.today():
                        dl = " (сегодня)"
                    else:
                        dl = f" (до {t.deadline})"
                est = est_map.get(t.priority, 35)
                task_lines.append(f"{idx}. {t.title}{dl} ~{est}м")
            tasks_block = "\n".join(task_lines)
        else:
            tasks_block = "1. Закрытых задач нет, начни с самой важной учебной цели."

        habits_due = []
        weekday_bit = 1 << date.today().weekday()
        for h in habits:
            if h.schedule_mask & weekday_bit:
                habits_due.append(f"• {h.emoji} {h.name} (🔥{h.current_streak})")
        habits_block = "\n".join(habits_due[:8]) if habits_due else "• Сегодня по расписанию нет обязательных привычек."

        done_block = "\n".join(f"• ✅ {t.title}" for t in done_today[:6]) if done_today else "• Пока ничего не отмечено."
        mentor_name = user.get_settings().get("mentor_name", "Ментор")
        return (
            f"🤖 {mentor_name}, план на сегодня ({now.strftime('%H:%M')})\n\n"
            f"📌 *Порядок действий:*\n{tasks_block}\n\n"
            f"🔄 *Привычки на сегодня:*\n{habits_block}\n\n"
            f"✅ *Уже сделано сегодня:*\n{done_block}\n\n"
            "Совет: начни с 1-й задачи, затем 5 минут перерыв, потом 2-ю. "
            "Если застрял, разбей задачу на 15-минутный шаг.\n\n"
            "Как у тебя дела? Если нужно, соберу микро-план на ближайшие 2 часа."
        )

    async def _call_with_fallback(
        self, system_prompt: str, context: str, message: str
    ) -> str:
        response = await self.primary_backend.generate(
            system_prompt=system_prompt,
            context=context,
            user_message=message,
            max_tokens=650,
        )

        if response.startswith("⚠️") and self.fallback_backend:
            logger.info("Primary AI failed, trying fallback")
            response = await self.fallback_backend.generate(
                system_prompt=system_prompt,
                context=context,
                user_message=message,
                max_tokens=650,
            )

        return response

    async def generate_summary(self, text: str) -> str:
        return await self.primary_backend.generate_summary(text)

    async def rewrite_journal_entry(self, text: str) -> str:
        prompt = (
            "Исправь орфографию и пунктуацию, сделай текст более читаемым, "
            "добавь аккуратные эмодзи по смыслу. "
            "Сохрани исходный смысл и краткость.\n\n"
            f"Текст:\n{text}"
        )
        return await self.primary_backend.generate(
            system_prompt="You are a Russian writing assistant. Keep markdown-safe formatting.",
            context="",
            user_message=prompt,
            max_tokens=550,
        )

    async def generate_weekly_review(self, user_id: int, metrics: dict) -> str:
        prompt = (
            f"Generate a weekly review for a developer based on these metrics:\n"
            f"- Tasks completed: {metrics['tasks_completed']}/{metrics['tasks_created']}\n"
            f"- Tasks overdue: {metrics['tasks_overdue']}\n"
            f"- Habit completion rate: {metrics['habit_rate']:.0%}\n"
            f"- Best streak: {metrics['best_streak']} days\n"
            f"- Journal entries: {metrics['journal_count']}\n"
            f"- XP earned: {metrics['xp_earned']}, XP lost: {metrics['xp_lost']}\n"
            f"- Discipline score: {metrics['discipline']:.0f}/100\n"
            f"- Growth score: {metrics['growth']:.0f}/100\n\n"
            f"Write 3-5 sentences in Russian: what went well, what needs improvement, "
            f"and one specific actionable recommendation for next week."
        )

        return await self.primary_backend.generate(
            system_prompt="You are a data-driven programming mentor analyzing weekly metrics. Respond in Russian.",
            context="",
            user_message=prompt,
            max_tokens=320,
        )
