from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.gamification_service import GamificationService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, db_user: User):
    level_info = GamificationService.format_level_progress(db_user.total_xp_earned)

    await message.answer(
        f"👋 Привет, *{db_user.first_name}*!\n\n"
        f"Я твой AI-наставник по программированию.\n\n"
        f"{level_info}\n\n"
        f"📋 Команды:\n"
        f"/task — управление задачами\n"
        f"/habit — трекер привычек\n"
        f"/journal — dev journal\n"
        f"/ai — чат с наставником\n"
        f"/stats — статистика и прогресс\n"
        f"/mode — режим AI наставника\n"
        f"/review — недельный обзор\n"
        f"/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(message: Message, **kwargs):
    await message.answer(
        "📖 *Помощь*\n\n"
        "*Задачи:*\n"
        "`/task add <название> #тег p:high d:2025-07-20`\n"
        "`/task list` — список задач\n"
        "`/task done <id>` — завершить\n"
        "`/task delete <id>` — удалить\n\n"
        "*Привычки:*\n"
        "`/habit add <название>` — создать\n"
        "`/habit check <id>` — отметить\n"
        "`/habit list` — список\n\n"
        "*Журнал:*\n"
        "`/journal add` — новая запись\n"
        "`/journal list` — список\n"
        "`/journal search <запрос>` — поиск\n\n"
        "*AI наставник:*\n"
        "`/ai <сообщение>` — задать вопрос\n\n"
        "*Прогресс:*\n"
        "`/stats` — статистика\n"
        "`/review` — недельный обзор\n"
        "`/mode strict/soft/adaptive` — режим AI"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, db_user: User):
    level_info = GamificationService.format_level_progress(db_user.total_xp_earned)

    d = db_user.discipline_score
    d_emoji = "🟢" if d >= 70 else ("🟡" if d >= 40 else "🔴")

    g = db_user.growth_score
    g_emoji = "🟢" if g >= 70 else ("🟡" if g >= 40 else "🔴")

    await message.answer(
        f"📊 *Твоя статистика*\n\n"
        f"{level_info}\n\n"
        f"{d_emoji} Discipline: {d:.0f}/100\n"
        f"{g_emoji} Growth: {g:.0f}/100\n\n"
        f"🤖 AI Mode: {db_user.ai_mode}\n"
        f"📅 Joined: {db_user.created_at.strftime('%Y-%m-%d')}"
    )