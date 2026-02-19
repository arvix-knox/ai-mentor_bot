from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.ai_service import AIService
from src.services.gamification_service import GamificationService
from src.bot.keyboards.inline import back_to_menu_keyboard

router = Router()


class AIStates(StatesGroup):
    waiting_message = State()


@router.message(Command("ai"))
async def cmd_ai(message: Message, session: AsyncSession, db_user: User):
    text = message.text.strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            f"🤖 *AI Наставник* ({db_user.ai_mode})\n\n"
            f"Задай вопрос:\n"
            f"`/ai Как изучать Python?`\n\n"
            f"Или просто напиши сообщение ⬇️",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    thinking_msg = await message.answer("🤔 Думаю...")
    ai_svc = AIService(session)
    response, elapsed_ms = await ai_svc.get_response(db_user.id, parts[1])
    await GamificationService(session).award_xp(db_user.id, "ai_session")
    seconds = elapsed_ms / 1000
    await thinking_msg.edit_text(
        f"🤖 *Наставник* ({db_user.ai_mode})\n\n{response}\n\n⏱ _{seconds:.1f}s_",
        reply_markup=back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:ai")
async def callback_ai_menu(callback: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    await state.set_state(AIStates.waiting_message)
    await callback.message.edit_text(
        f"🤖 *AI Наставник* ({db_user.ai_mode})\n\n"
        f"Напиши свой вопрос:",
    )
    await callback.answer()


@router.message(AIStates.waiting_message)
async def ai_message_received(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    thinking_msg = await message.answer("🤔 Думаю...")
    ai_svc = AIService(session)
    response, elapsed_ms = await ai_svc.get_response(db_user.id, message.text)
    await GamificationService(session).award_xp(db_user.id, "ai_session")
    seconds = elapsed_ms / 1000
    await thinking_msg.edit_text(
        f"🤖 *Наставник*\n\n{response}\n\n⏱ _{seconds:.1f}s_",
        reply_markup=back_to_menu_keyboard(),
    )
    await state.clear()


@router.message(F.text == "🤖 AI")
async def reply_ai(message: Message, session: AsyncSession, db_user: User):
    await message.answer(
        f"🤖 *AI Наставник* ({db_user.ai_mode})\n\n"
        f"Напиши `/ai Твой вопрос`",
        reply_markup=back_to_menu_keyboard(),
    )
