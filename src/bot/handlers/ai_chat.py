from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.ai_service import AIService
from src.services.gamification_service import GamificationService
from src.bot.keyboards.inline import back_keyboard, main_menu_keyboard

router = Router()


class AIStates(StatesGroup):
    chatting = State()


@router.message(Command("ai"))
async def cmd_ai(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await state.set_state(AIStates.chatting)
        await message.answer(
            f"🤖 *AI Наставник* ({db_user.ai_mode})\n\n"
            f"Напиши вопрос. Для выхода нажми кнопку.",
            reply_markup=back_keyboard("menu:main"),
        )
        return
    await _process_ai_message(message, session, db_user, parts[1])


@router.callback_query(F.data == "menu:ai")
async def cb_ai_menu(callback: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    await state.set_state(AIStates.chatting)
    try:
        await callback.message.edit_text(
            f"🤖 *AI Наставник* ({db_user.ai_mode})\n\nНапиши свой вопрос:",
            reply_markup=back_keyboard("menu:main"),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AIStates.chatting)
async def ai_chat_message(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    await _process_ai_message(message, session, db_user, message.text)


async def _process_ai_message(message: Message, session, db_user, user_text: str):
    thinking = await message.answer("🤔 Думаю...")
    ai_svc = AIService(session)
    response, elapsed_ms = await ai_svc.get_response(db_user.id, user_text)
    await GamificationService(session).award_xp(db_user.id, "ai_session")
    seconds = elapsed_ms / 1000
    try:
        await thinking.edit_text(
            f"🤖 *Наставник* ({db_user.ai_mode})\n\n{response}\n\n_⏱ {seconds:.1f}s | +5 XP_",
            reply_markup=back_keyboard("menu:main"),
        )
    except TelegramBadRequest:
        await thinking.edit_text(
            f"🤖 Ответ получен\n\n_⏱ {seconds:.1f}s_",
            reply_markup=back_keyboard("menu:main"),
        )


@router.message(F.text == "🤖 AI")
async def reply_ai(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    await state.set_state(AIStates.chatting)
    await message.answer(
        f"🤖 *AI Наставник* ({db_user.ai_mode})\n\nНапиши вопрос:",
        reply_markup=back_keyboard("menu:main"),
    )
