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
from src.bot.keyboards.inline import back_keyboard

router = Router()


class AIStates(StatesGroup):
    chatting = State()


@router.message(Command("ai"))
async def cmd(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await state.set_state(AIStates.chatting)
        await message.answer(f"🤖 *AI* ({db_user.ai_mode})\n\nНапиши вопрос:", reply_markup=back_keyboard("menu:main"))
        return
    await _ai(message, session, db_user, parts[1])


@router.callback_query(F.data == "menu:ai")
async def cb(callback: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    await state.set_state(AIStates.chatting)
    try:
        await callback.message.edit_text(f"🤖 *AI* ({db_user.ai_mode})\n\nНапиши:", reply_markup=back_keyboard("menu:main"))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AIStates.chatting)
async def st_chat(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    await _ai(message, session, db_user, message.text)


async def _ai(message, session, db_user, text):
    t = await message.answer("🤔 Думаю...")
    svc = AIService(session)
    resp, ms = await svc.get_response(db_user.id, text)
    await GamificationService(session).award_xp(db_user.id, "ai_session")
    s = ms / 1000
    try:
        await t.edit_text(f"🤖 ({db_user.ai_mode})\n\n{resp}\n\n_⏱{s:.1f}s +5XP_", reply_markup=back_keyboard("menu:main"))
    except TelegramBadRequest:
        try:
            await t.edit_text(f"🤖 Ответ получен _⏱{s:.1f}s_", reply_markup=back_keyboard("menu:main"))
        except TelegramBadRequest:
            pass


@router.message(F.text == "🤖 AI")
async def reply(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    await state.set_state(AIStates.chatting)
    await message.answer(f"🤖 *AI* ({db_user.ai_mode})\n\nНапиши:", reply_markup=back_keyboard("menu:main"))
