from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.gamification_service import GamificationService
from src.bot.keyboards.inline import main_menu_keyboard, back_keyboard
from src.bot.keyboards.reply import main_reply_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, db_user: User):
    level_info = GamificationService.format_level_progress(db_user.total_xp_earned)
    await message.answer(
        f"👋 Привет, *{db_user.first_name}*!\n\n"
        f"Я твой AI-наставник по программированию 🚀\n\n"
        f"{level_info}",
        reply_markup=main_reply_keyboard(),
    )
    await message.answer("🏠 *Главное меню*", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:main")
async def callback_main_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🏠 *Главное меню*", reply_markup=main_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, **kwargs):
    await message.answer(
        "📖 *Команды*\n\n"
        "📋 `/task add Название #тег p:high`\n"
        "🔄 `/habit add 📚 Читать`\n"
        "📝 `/journal add`\n"
        "🤖 `/ai Твой вопрос`\n"
        "📊 `/stats` — статистика\n"
        "📈 `/review` — обзор недели\n"
        "⚙️ `/mode` — режим AI\n\n"
        "Или используй кнопки 👇",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, db_user: User):
    await _show_stats(message, db_user)


@router.callback_query(F.data == "menu:stats")
async def callback_stats(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await _show_stats(callback.message, db_user, edit=True)
    await callback.answer()


@router.message(F.text == "📊 Статистика")
async def reply_stats(message: Message, session: AsyncSession, db_user: User):
    await _show_stats(message, db_user)


async def _show_stats(message, db_user, edit=False):
    level_info = GamificationService.format_level_progress(db_user.total_xp_earned)
    d = db_user.discipline_score
    d_emoji = "🟢" if d >= 70 else ("🟡" if d >= 40 else "🔴")
    d_bar = "▓" * int(d / 10) + "░" * (10 - int(d / 10))
    g = db_user.growth_score
    g_emoji = "🟢" if g >= 70 else ("🟡" if g >= 40 else "🔴")
    g_bar = "▓" * int(g / 10) + "░" * (10 - int(g / 10))
    text = (
        f"📊 *Статистика*\n\n"
        f"{level_info}\n\n"
        f"{d_emoji} Discipline [{d_bar}] {d:.0f}/100\n"
        f"{g_emoji} Growth [{g_bar}] {g:.0f}/100\n\n"
        f"🤖 Режим: *{db_user.ai_mode}*\n"
        f"📅 С нами с {db_user.created_at.strftime('%d.%m.%Y')}"
    )
    kb = back_keyboard("menu:main")
    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            pass
    else:
        await message.answer(text, reply_markup=kb)
