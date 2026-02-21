import re
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
from src.services.task_service import TaskService
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
    lowered = (text or "").lower()
    settings_data = db_user.get_settings()
    ai_perms = settings_data.get("ai_permissions", {})

    if lowered.startswith("добавь задачу") and ai_perms.get("create_tasks", True):
        raw = text[len("добавь задачу"):].strip(" :.-")
        if not raw:
            await message.answer("Формат: `добавь задачу <название> [HH:MM]`", reply_markup=back_keyboard("menu:main"))
            return
        time_match = re.search(r"\b([01]\d|2[0-3]):([0-5]\d)\b", raw)
        remind_time = time_match.group(0) if time_match else None
        title = re.sub(r"\b([01]\d|2[0-3]):([0-5]\d)\b", "", raw).strip()
        task = await TaskService(session).create_task(
            user_id=db_user.id,
            title=title,
            remind_enabled=bool(remind_time),
            remind_time=remind_time,
            remind_text=f"🔔 Пора выполнять: {title}",
        )
        await message.answer(f"✅ Задача создана: *{task['title']}*", reply_markup=back_keyboard("menu:main"))
        return

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
