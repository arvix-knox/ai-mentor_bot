from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.user_repo import UserRepository
from src.services.analytics_service import AnalyticsService
from src.bot.keyboards.inline import ai_mode_keyboard, back_keyboard, main_menu_keyboard

router = Router()

MODE_DESC = {
    "strict": "🔴 *Strict* — жёсткий, требовательный",
    "soft": "🟢 *Soft* — мягкий, поддерживающий",
    "adaptive": "🟡 *Adaptive* — подстраивается под метрики",
}


@router.message(Command("mode"))
async def cmd_mode(message: Message, session: AsyncSession, db_user: User):
    await message.answer(
        f"⚙️ *Режим AI*\n\nТекущий: {MODE_DESC[db_user.ai_mode]}",
        reply_markup=ai_mode_keyboard(db_user.ai_mode),
    )


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery, session: AsyncSession, db_user: User):
    try:
        await callback.message.edit_text(
            f"⚙️ *Настройки*\n\nРежим AI: {MODE_DESC[db_user.ai_mode]}",
            reply_markup=ai_mode_keyboard(db_user.ai_mode),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(callback: CallbackQuery, session: AsyncSession, db_user: User):
    mode = callback.data.split(":")[1]
    if mode not in ("strict", "soft", "adaptive"):
        await callback.answer("Неверный режим")
        return
    user_repo = UserRepository(session)
    await user_repo.update(db_user.id, ai_mode=mode)
    db_user.ai_mode = mode
    try:
        await callback.message.edit_text(
            f"✅ Режим: {MODE_DESC[mode]}",
            reply_markup=ai_mode_keyboard(mode),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("Сохранено!")


@router.message(Command("review"))
async def cmd_review(message: Message, session: AsyncSession, db_user: User):
    msg = await message.answer("📊 Генерирую обзор недели...")
    analytics_svc = AnalyticsService(session)
    data = await analytics_svc.generate_weekly_report(db_user.id)
    report = AnalyticsService.format_weekly_report(data)
    try:
        await msg.edit_text(report, reply_markup=back_keyboard("menu:main"))
    except TelegramBadRequest:
        await msg.edit_text("📊 Обзор сгенерирован", reply_markup=back_keyboard("menu:main"))


@router.callback_query(F.data == "menu:review")
async def cb_review(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer("Генерирую...")
    try:
        await callback.message.edit_text("📊 Генерирую обзор...")
    except TelegramBadRequest:
        pass
    analytics_svc = AnalyticsService(session)
    data = await analytics_svc.generate_weekly_report(db_user.id)
    report = AnalyticsService.format_weekly_report(data)
    try:
        await callback.message.edit_text(report, reply_markup=back_keyboard("menu:main"))
    except TelegramBadRequest:
        pass


@router.message(F.text == "📈 Обзор")
async def reply_review(message: Message, session: AsyncSession, db_user: User):
    await cmd_review(message, session=session, db_user=db_user)
