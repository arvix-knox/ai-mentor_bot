from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.ai_service import AIService
from src.services.gamification_service import GamificationService

router = Router()


@router.message(Command("ai"))
async def cmd_ai(message: Message, session: AsyncSession, db_user: User):
    text = message.text.strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "🤖 *AI Наставник*\n\n"
            "Задай мне вопрос:\n"
            "`/ai Как лучше изучать Python?`\n"
            "`/ai Чувствую что застрял, что делать?`\n"
            "`/ai Ревью моего прогресса`\n\n"
            f"Текущий режим: *{db_user.ai_mode}*\n"
            "Сменить: `/mode strict/soft/adaptive`"
        )
        return

    user_message = parts[1]

    thinking_msg = await message.answer("🤔 Думаю...")

    ai_svc = AIService(session)
    response, elapsed_ms = await ai_svc.get_response(db_user.id, user_message)

    await GamificationService(session).award_xp(
        db_user.id, "ai_session",
        source_type="ai",
    )

    await thinking_msg.edit_text(
        f"🤖 *AI Наставник* ({db_user.ai_mode})\n\n"
        f"{response}\n\n"
        f"_{elapsed_ms}ms_"
    )