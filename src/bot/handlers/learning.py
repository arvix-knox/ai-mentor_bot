from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.learning_service import LearningService
from src.repositories.learning_repo import LearningRepository
from src.services.achievement_service import AchievementService
from src.bot.keyboards.inline import (
    learning_menu_keyboard,
    learning_type_keyboard,
    learning_list_keyboard,
    learning_item_keyboard,
    back_keyboard,
)

router = Router()

RESOURCE_NAMES = {
    "article": "📄 Статья",
    "video": "🎬 Видео",
    "course": "🎓 Курс",
    "summary": "⚡ Кратко",
}


class LearningStates(StatesGroup):
    waiting_type = State()
    waiting_title = State()
    waiting_topic = State()
    waiting_url = State()
    waiting_suggest_topic = State()


@router.message(Command("learning"))
async def cmd_learning(message: Message):
    await message.answer("🎓 *Обучение*", reply_markup=learning_menu_keyboard())


@router.callback_query(F.data == "menu:learning")
async def cb_menu_learning(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🎓 *Обучение*", reply_markup=learning_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(F.text == "🎓 Обучение")
async def reply_learning(message: Message):
    await message.answer("🎓 *Обучение*", reply_markup=learning_menu_keyboard())


@router.callback_query(F.data == "learn:add")
async def cb_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LearningStates.waiting_type)
    await callback.message.edit_text("Выбери тип ресурса:", reply_markup=learning_type_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("learn:type:"))
async def cb_type(callback: CallbackQuery, state: FSMContext):
    rtype = callback.data.split(":")[2]
    await state.update_data(resource_type=rtype)
    await state.set_state(LearningStates.waiting_title)
    await callback.message.edit_text(f"{RESOURCE_NAMES.get(rtype, rtype)}\n\nОтправь название:")
    await callback.answer()


@router.message(LearningStates.waiting_title)
async def st_title(message: Message, state: FSMContext):
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(LearningStates.waiting_topic)
    await message.answer("Укажи тему (например FastAPI):")


@router.message(LearningStates.waiting_topic)
async def st_topic(message: Message, state: FSMContext):
    await state.update_data(topic=(message.text or "").strip())
    await state.set_state(LearningStates.waiting_url)
    await message.answer("Ссылка (или '-' если нет):")


@router.message(LearningStates.waiting_url)
async def st_url(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = await state.get_data()
    url_text = (message.text or "").strip()
    url = None if url_text == "-" else url_text
    svc = LearningService(session)
    result = await svc.add_resource(
        user_id=db_user.id,
        resource_type=data["resource_type"],
        title=data["title"],
        url=url,
        topic=data.get("topic"),
    )
    await AchievementService(session).evaluate(db_user.id)
    await message.answer(f"✅ Добавлено: *{result['title']}*", reply_markup=learning_menu_keyboard())
    await state.clear()


@router.callback_query(F.data == "learn:list")
async def cb_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    rows = await LearningService(session).get_user_resources(db_user.id)
    if not rows:
        try:
            await callback.message.edit_text("🎓 Ресурсов пока нет", reply_markup=learning_menu_keyboard())
        except TelegramBadRequest:
            pass
        await callback.answer()
        return
    try:
        await callback.message.edit_text("🎓 *Мои ресурсы:*", reply_markup=learning_list_keyboard(rows))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("learn:view:"))
async def cb_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    rid = int(callback.data.split(":")[2])
    repo = LearningRepository(session)
    row = await repo.get_by_id(rid)
    if not row or row.user_id != db_user.id:
        await callback.answer("Не найдено")
        return
    text = (
        f"{RESOURCE_NAMES.get(row.resource_type, row.resource_type)} *{row.title}*\n\n"
        f"Тема: {row.topic or '—'}\n"
        f"Ссылка: {row.url or '—'}\n"
        f"Статус: {'✅ пройдено' if row.is_completed else '📌 в процессе'}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=learning_item_keyboard(row.id, row.is_completed))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("learn:done:"))
async def cb_done(callback: CallbackQuery, session: AsyncSession, db_user: User):
    rid = int(callback.data.split(":")[2])
    result = await LearningService(session).mark_done(db_user.id, rid)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    await AchievementService(session).evaluate(db_user.id)
    await callback.answer("✅ Отмечено")
    try:
        await callback.message.edit_text(
            f"✅ *{result['title']}* отмечено как пройдено",
            reply_markup=back_keyboard("learn:list"),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("learn:del:"))
async def cb_del(callback: CallbackQuery, session: AsyncSession, db_user: User):
    rid = int(callback.data.split(":")[2])
    repo = LearningRepository(session)
    row = await repo.get_by_id(rid)
    if not row or row.user_id != db_user.id:
        await callback.answer("Нет доступа")
        return
    await repo.delete(rid)
    await callback.answer("Удалено")
    try:
        await callback.message.edit_text("🗑 Ресурс удален", reply_markup=learning_menu_keyboard())
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "learn:suggest")
async def cb_suggest(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LearningStates.waiting_suggest_topic)
    await callback.message.edit_text("Введите тему для подборки (например FastAPI):")
    await callback.answer()


@router.message(LearningStates.waiting_suggest_topic)
async def st_suggest_topic(message: Message, session: AsyncSession, state: FSMContext):
    topic = (message.text or "").strip()
    items = await LearningService(session).suggest(topic)
    lines = [
        f"{RESOURCE_NAMES.get(x['resource_type'], x['resource_type'])} *{x['title']}*\n{x.get('url', '—')}"
        for x in items
    ]
    await message.answer(
        "🧠 *Рекомендации:*\n\n" + "\n\n".join(lines),
        reply_markup=learning_menu_keyboard(),
    )
    await state.clear()
