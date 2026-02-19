from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.user_repo import UserRepository
from src.services.analytics_service import AnalyticsService

router = Router()

VALID_MODES = {"strict", "soft", "adaptive"}

MODE_DESCRIPTIONS = {
    "strict": "🔴 *Strict* — жёсткий наставник, без поблажек",
    "soft": "🟢 *Soft* — мягкий наставник, поддержка и эмпатия",
    "adaptive": "🟡 *Adaptive* — подстраивается под твои метрики",
}


def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 Strict", callback_data="mode:strict"),
            InlineKeyboardButton(text="🟢 Soft", callback_data="mode:soft"),
            InlineKeyboardButton(text="🟡 Adaptive", callback_data="mode:adaptive"),
        ]
    ])


@router.message(Command("mode"))
async def cmd_mode(message: Message, session: AsyncSession, db_user: User):
    text = message.text.strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            f"🤖 *Режим AI наставника*\n\n"
            f"Текущий: {MODE_DESCRIPTIONS[db_user.ai_mode]}\n\n"
            f"Выбери режим:",
            reply_markup=mode_keyboard(),
        )
        return

    mode = parts[1].lower().strip()
    if mode not in VALID_MODES:
        await message.answer(
            f"❌ Неверный режим. Доступны: strict, soft, adaptive"
        )
        return

    user_repo = UserRepository(session)
    await user_repo.update(db_user.id, ai_mode=mode)

    await message.answer(f"✅ Режим изменён:\n{MODE_DESCRIPTIONS[mode]}")


@router.callback_query(lambda c: c.data and c.data.startswith("mode:"))
async def callback_mode(callback: CallbackQuery, session: AsyncSession, db_user: User):
    mode = callback.data.split(":")[1]

    if mode not in VALID_MODES:
        await callback.answer("Неверный режим")
        return

    user_repo = UserRepository(session)
    await user_repo.update(db_user.id, ai_mode=mode)

    await callback.message.edit_text(
        f"✅ Режим изменён:\n{MODE_DESCRIPTIONS[mode]}"
    )
    await callback.answer("Done!")


@router.message(Command("review"))
async def cmd_review(message: Message, session: AsyncSession, db_user: User):
    await message.answer("📊 Генерирую недельный обзор...")

    analytics_svc = AnalyticsService(session)
    data = await analytics_svc.generate_weekly_report(db_user.id)
    report_text = AnalyticsService.format_weekly_report(data)

    await message.answer(report_text)