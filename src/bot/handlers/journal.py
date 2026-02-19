from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.journal_service import JournalService
from src.bot.keyboards.inline import journal_menu_keyboard, journal_entry_keyboard, journal_list_keyboard, back_keyboard

router = Router()


class JournalStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    waiting_search = State()


@router.message(Command("journal"))
async def cmd_journal(message: Message, **kwargs):
    await message.answer("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())


@router.callback_query(F.data == "menu:journal")
async def cb_journal_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "journal:add")
async def cb_journal_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalStates.waiting_title)
    await callback.message.edit_text("📝 *Новая запись*\n\nОтправь *заголовок*:")
    await callback.answer()


@router.message(JournalStates.waiting_title)
async def journal_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(JournalStates.waiting_content)
    await message.answer("✏️ Теперь *содержание*.\nИспользуй #теги:\n`Изучил async #python #async`")


@router.message(JournalStates.waiting_content)
async def journal_content(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = await state.get_data()
    journal_svc = JournalService(session)
    result = await journal_svc.create_entry(user_id=db_user.id, title=data["title"], content=message.text.strip())
    tags = " ".join(f"#{t}" for t in result["tags"]) if result["tags"] else ""
    level_msg = "\n🎉 *LEVEL UP!*" if result.get("leveled_up") else ""
    await message.answer(
        f"📝 Записано: *{result['title']}*\n{tags}\n+{result['xp_earned']} XP ⭐{level_msg}",
        reply_markup=journal_menu_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data == "journal:list")
async def cb_journal_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    journal_svc = JournalService(session)
    entries = await journal_svc.get_entries(db_user.id, limit=8)
    if not entries:
        try:
            await callback.message.edit_text("📝 Журнал пуст", reply_markup=journal_menu_keyboard())
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text("📝 *Записи* — нажми для просмотра:", reply_markup=journal_list_keyboard(entries))
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("journal:view:"))
async def cb_journal_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    entry_id = int(callback.data.split(":")[2])
    from src.repositories.journal_repo import JournalRepository
    journal_repo = JournalRepository(session)
    entry = await journal_repo.get_by_id(entry_id)
    if not entry or entry.user_id != db_user.id:
        await callback.answer("Не найдено")
        return
    tags = " ".join(f"#{t}" for t in (entry.tags or []))
    text = (
        f"📝 *{entry.title}*\n"
        f"_{entry.created_at.strftime('%d.%m.%Y %H:%M')}_\n"
        f"{tags}\n\n"
        f"{entry.content[:3000]}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=journal_entry_keyboard(entry_id))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("journal:del:"))
async def cb_journal_del(callback: CallbackQuery, session: AsyncSession, db_user: User):
    entry_id = int(callback.data.split(":")[2])
    journal_svc = JournalService(session)
    result = await journal_svc.delete_entry(db_user.id, entry_id)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    try:
        await callback.message.edit_text(f"🗑 Удалено: *{result['title']}*", reply_markup=journal_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer("Удалено")


@router.callback_query(F.data == "journal:search")
async def cb_journal_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalStates.waiting_search)
    await callback.message.edit_text("🔍 Отправь запрос или #тег:")
    await callback.answer()


@router.message(JournalStates.waiting_search)
async def journal_search_input(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    query = message.text.strip()
    journal_svc = JournalService(session)
    if query.startswith("#"):
        entries = await journal_svc.get_entries(db_user.id, tag=query.lstrip("#"))
    else:
        entries = await journal_svc.get_entries(db_user.id, query=query)
    if not entries:
        await message.answer(f"🔍 Ничего: _{query}_", reply_markup=journal_menu_keyboard())
    else:
        await message.answer(f"🔍 *Результаты:* _{query}_", reply_markup=journal_list_keyboard(entries))
    await state.clear()


@router.message(F.text == "📝 Журнал")
async def reply_journal(message: Message):
    await message.answer("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())
