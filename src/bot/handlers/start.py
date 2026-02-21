from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.gamification_service import GamificationService
from src.bot.keyboards.inline import main_menu_keyboard, back_keyboard, webapp_open_keyboard
from src.bot.keyboards.reply import main_reply_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, db_user: User):
    level_info = GamificationService.format_level_progress(db_user.total_xp_earned)
    has_stack = bool(db_user.tech_stack)
    setup_hint = "" if has_stack else "\n\n💡 Настрой профиль: 👤 *Профиль*"
    await message.answer(
        f"👋 Привет, *{db_user.get_display_name()}*!\n\n"
        f"Я твой AI-наставник 🚀\n\n"
        f"{level_info}{setup_hint}",
        reply_markup=main_reply_keyboard(),
    )
    await message.answer("🏠 *Главное меню*", reply_markup=main_menu_keyboard())
    await message.answer("🌐 Открой web-приложение для полного функционала:", reply_markup=webapp_open_keyboard())


@router.callback_query(F.data == "menu:main")
async def cb_main(callback: CallbackQuery):
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
        "🤖 `/ai Вопрос`\n"
        "🌐 `/webapp`\n"
        "🎓 `/learning`\n"
        "🎵 `/playlist`\n"
        "📊 `/stats` | 📈 `/review`\n"
        "👤 `/profile` | ⚙️ `/settings`\n\n"
        "Или кнопки 👇",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("webapp"))
async def cmd_webapp(message: Message):
    await message.answer("🌐 Открой Web App:", reply_markup=webapp_open_keyboard())


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, db_user: User):
    await _send_stats(message, db_user)


@router.callback_query(F.data == "menu:stats")
async def cb_stats(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await _send_stats(callback.message, db_user, edit=True)
    await callback.answer()


@router.message(F.text == "📊 Стата")
async def reply_stats(message: Message, session: AsyncSession, db_user: User):
    await _send_stats(message, db_user)


async def _send_stats(msg, user, edit=False):
    li = GamificationService.format_level_progress(user.total_xp_earned)
    d = user.discipline_score
    de = "🟢" if d >= 70 else ("🟡" if d >= 40 else "🔴")
    db = "▓" * int(d / 10) + "░" * (10 - int(d / 10))
    g = user.growth_score
    ge = "🟢" if g >= 70 else ("🟡" if g >= 40 else "🔴")
    gb = "▓" * int(g / 10) + "░" * (10 - int(g / 10))
    import json
    stack = []
    try:
        if user.tech_stack:
            stack = json.loads(user.tech_stack)
    except Exception:
        pass
    stack_text = ", ".join(stack) if stack else "не указан"
    text = (
        f"📊 *Статистика*\n\n"
        f"{li}\n\n"
        f"{de} Discipline [{db}] {d:.0f}/100\n"
        f"{ge} Growth [{gb}] {g:.0f}/100\n\n"
        f"💻 Стек: {stack_text}\n"
        f"🤖 Режим: *{user.ai_mode}*\n"
        f"📅 С нами с {user.created_at.strftime('%d.%m.%Y')}"
    )
    kb = back_keyboard("menu:main")
    if edit:
        try:
            await msg.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            pass
    else:
        await msg.answer(text, reply_markup=kb)
