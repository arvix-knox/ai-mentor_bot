import time
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.services.ai_backends.base import BaseAIBackend
from src.services.ai_backends.groq_backend import GroqBackend
from src.services.ai_backends.openrouter_backend import OpenRouterBackend
from src.services.memory_service import MemoryService
from src.repositories.memory_repo import MemoryRepository
from src.repositories.user_repo import UserRepository

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
}


class AIService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memory_service = MemoryService(session)
        self.memory_repo = MemoryRepository(session)
        self.user_repo = UserRepository(session)
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
        context = await self.memory_service.build_context(user_id)
        system_prompt = PERSONALITY_PROMPTS.get(user.ai_mode, PERSONALITY_PROMPTS["adaptive"])

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

    async def _call_with_fallback(
        self, system_prompt: str, context: str, message: str
    ) -> str:
        response = await self.primary_backend.generate(
            system_prompt=system_prompt,
            context=context,
            user_message=message,
            max_tokens=800,
        )

        if response.startswith("⚠️") and self.fallback_backend:
            logger.info("Primary AI failed, trying fallback")
            response = await self.fallback_backend.generate(
                system_prompt=system_prompt,
                context=context,
                user_message=message,
                max_tokens=800,
            )

        return response

    async def generate_summary(self, text: str) -> str:
        return await self.primary_backend.generate_summary(text)

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
            max_tokens=400,
        )