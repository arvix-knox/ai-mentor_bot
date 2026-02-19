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
async def cmd(message: Message, **kwargs):
    await message.answer("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())


@router.callback_query(F.data == "menu:journal")
async def cb_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "journal:add")
async def cb_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalStates.waiting_title)
    await callback.message.edit_text("📝 *Новая запись*\n\nОтправь *заголовок*:")
    await callback.answer()


@router.message(JournalStates.waiting_title)
async def st_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(JournalStates.waiting_content)
    await message.answer("✏️ Теперь *содержание* с #тегами:")


@router.message(JournalStates.waiting_content)
async def st_content(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    d = await state.get_data()
    svc = JournalService(session)
    r = await svc.create_entry(user_id=db_user.id, title=d["title"], content=message.text.strip())
    tags = " ".join(f"#{t}" for t in r["tags"]) if r["tags"] else ""
    lm = "\n🎉 *LEVEL UP!*" if r.get("leveled_up") else ""
    await message.answer(f"📝 *{r['title']}*\n{tags}\n+{r['xp_earned']} XP ⭐{lm}", reply_markup=journal_menu_keyboard())
    await state.clear()


@router.callback_query(F.data == "journal:list")
async def cb_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    svc = JournalService(session)
    entries = await svc.get_entries(db_user.id, limit=8)
    if entries:
        try:
            await callback.message.edit_text("📝 *Записи:*", reply_markup=journal_list_keyboard(entries))
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text("📝 Пусто", reply_markup=journal_menu_keyboard())
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("journal:view:"))
async def cb_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    eid = int(callback.data.split(":")[2])
    from src.repositories.journal_repo import JournalRepository
    repo = JournalRepository(session)
    e = await repo.get_by_id(eid)
    if not e or e.user_id != db_user.id:
        await callback.answer("Нет")
        return
    tags = " ".join(f"#{t}" for t in (e.tags or []))
    text = f"📝 *{e.title}*\n_{e.created_at.strftime('%d.%m.%Y %H:%M')}_\n{tags}\n\n{e.content[:3500]}"
    try:
        await callback.message.edit_text(text, reply_markup=journal_entry_keyboard(eid))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("journal:related:"))
async def cb_related(callback: CallbackQuery, session: AsyncSession, db_user: User):
    eid = int(callback.data.split(":")[2])
    svc = JournalService(session)
    related = await svc.get_related(eid, db_user.id)
    if not related:
        await callback.answer("Нет связанных")
        return
    try:
        await callback.message.edit_text("🔗 *Связанные:*", reply_markup=journal_list_keyboard(related))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("journal:del:"))
async def cb_del(callback: CallbackQuery, session: AsyncSession, db_user: User):
    eid = int(callback.data.split(":")[2])
    svc = JournalService(session)
    r = await svc.delete_entry(db_user.id, eid)
    if r.get("error"):
        await callback.answer(r["error"])
        return
    try:
        await callback.message.edit_text(f"🗑 *{r['title']}*", reply_markup=journal_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer("Удалено")


@router.callback_query(F.data == "journal:search")
async def cb_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalStates.waiting_search)
    await callback.message.edit_text("🔍 Запрос или #тег:")
    await callback.answer()


@router.callback_query(F.data == "journal:bytag")
async def cb_bytag(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalStates.waiting_search)
    await callback.message.edit_text("🏷 Введи #тег:")
    await callback.answer()


@router.message(JournalStates.waiting_search)
async def st_search(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    q = message.text.strip()
    svc = JournalService(session)
    if q.startswith("#"):
        entries = await svc.get_entries(db_user.id, tag=q.lstrip("#"))
    else:
        entries = await svc.get_entries(db_user.id, query=q)
    if entries:
        await message.answer(f"🔍 *{q}:*", reply_markup=journal_list_keyboard(entries))
    else:
        await message.answer(f"🔍 Пусто: _{q}_", reply_markup=journal_menu_keyboard())
    await state.clear()


@router.message(F.text == "📝 Журнал")
async def reply(message: Message):
    await message.answer("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())
