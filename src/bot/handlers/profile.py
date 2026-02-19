from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.user_repo import UserRepository
from src.services.analytics_service import AnalyticsService
from src.bot.keyboards.inline import ai_mode_keyboard, back_to_menu_keyboard

router = Router()

MODE_DESCRIPTIONS = {
    "strict": "🔴 *Strict* — жёсткий, без поблажек",
    "soft": "🟢 *Soft* — мягкий, поддерживающий",
    "adaptive": "🟡 *Adaptive* — подстраивается под метрики",
}


@router.message(Command("mode"))
async def cmd_mode(message: Message, session: AsyncSession, db_user: User):
    await message.answer(
        f"🤖 *Режим AI*\n\nТекущий: {MODE_DESCRIPTIONS[db_user.ai_mode]}",
        reply_markup=ai_mode_keyboard(db_user.ai_mode),
    )


@router.callback_query(F.data == "menu:settings")
async def callback_settings(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.message.edit_text(
        f"⚙️ *Настройки*\n\nРежим AI: {MODE_DESCRIPTIONS[db_user.ai_mode]}",
        reply_markup=ai_mode_keyboard(db_user.ai_mode),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mode:"))
async def callback_mode(callback: CallbackQuery, session: AsyncSession, db_user: User):
    mode = callback.data.split(":")[1]
    if mode not in ("strict", "soft", "adaptive"):
        await callback.answer("Неверный режим")
        return
    user_repo = UserRepository(session)
    await user_repo.update(db_user.id, ai_mode=mode)
    db_user.ai_mode = mode
    await callback.message.edit_text(
        f"✅ Режим изменён:\n{MODE_DESCRIPTIONS[mode]}",
        reply_markup=ai_mode_keyboard(mode),
    )
    await callback.answer("Сохранено!")


@router.message(Command("review"))
async def cmd_review(message: Message, session: AsyncSession, db_user: User):
    msg = await message.answer("📊 Генерирую обзор...")
    analytics_svc = AnalyticsService(session)
    data = await analytics_svc.generate_weekly_report(db_user.id)
    report = AnalyticsService.format_weekly_report(data)
    await msg.edit_text(report, reply_markup=back_to_menu_keyboard())


@router.message(F.text == "📈 Обзор недели")
async def reply_review(message: Message, session: AsyncSession, db_user: User):
    await cmd_review(message, session=session, db_user=db_user)
