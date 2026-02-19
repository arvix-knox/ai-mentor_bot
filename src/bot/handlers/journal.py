from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.journal_service import JournalService
from src.bot.keyboards.inline import journal_menu_keyboard, back_to_menu_keyboard

router = Router()


class JournalStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    waiting_search = State()


@router.message(Command("journal"))
async def cmd_journal(message: Message, session: AsyncSession, db_user: User):
    await message.answer("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())


@router.callback_query(F.data == "menu:journal")
async def callback_journal_menu(callback: CallbackQuery):
    await callback.message.edit_text("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "journal:add")
async def callback_journal_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalStates.waiting_title)
    await callback.message.edit_text(
        "📝 *Новая запись*\n\nОтправь *заголовок*:"
    )
    await callback.answer()


@router.message(JournalStates.waiting_title)
async def journal_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(JournalStates.waiting_content)
    await message.answer(
        "✏️ Теперь отправь *содержание*.\n\n"
        "Используй Markdown и #теги:\n"
        "`Изучил async/await в Python #python #async`"
    )


@router.message(JournalStates.waiting_content)
async def journal_content(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = await state.get_data()
    journal_svc = JournalService(session)
    result = await journal_svc.create_entry(
        user_id=db_user.id,
        title=data["title"],
        content=message.text.strip(),
    )
    tags_str = " ".join(f"#{t}" for t in result["tags"]) if result["tags"] else ""
    level_msg = "\n🎉 *LEVEL UP!*" if result.get("leveled_up") else ""
    await message.answer(
        f"📝 Записано: *{result['title']}*\n"
        f"{tags_str}\n"
        f"+{result['xp_earned']} XP ⭐{level_msg}",
        reply_markup=journal_menu_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data == "journal:list")
async def callback_journal_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    journal_svc = JournalService(session)
    entries = await journal_svc.get_entries(db_user.id, limit=10)
    if not entries:
        await callback.message.edit_text("📝 Журнал пуст", reply_markup=journal_menu_keyboard())
        await callback.answer()
        return
    lines = []
    for e in entries:
        tags_str = " ".join(f"#{t}" for t in (e.tags or []))
        date_str = e.created_at.strftime("%d.%m.%Y")
        preview = e.content[:60].replace("\n", " ")
        lines.append(f"📄 *{e.title}* — _{date_str}_\n   {preview}... {tags_str}")
    await callback.message.edit_text(
        "📝 *Последние записи:*\n\n" + "\n\n".join(lines),
        reply_markup=journal_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "journal:search")
async def callback_journal_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(JournalStates.waiting_search)
    await callback.message.edit_text("🔍 Отправь поисковый запрос или #тег:")
    await callback.answer()


@router.message(JournalStates.waiting_search)
async def journal_search(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    query = message.text.strip()
    journal_svc = JournalService(session)
    if query.startswith("#"):
        entries = await journal_svc.get_entries(db_user.id, tag=query.lstrip("#"))
    else:
        entries = await journal_svc.get_entries(db_user.id, query=query)
    if not entries:
        await message.answer(f"🔍 Ничего не найдено: _{query}_", reply_markup=journal_menu_keyboard())
    else:
        lines = [f"📄 *{e.title}* — _{e.created_at.strftime('%d.%m.%Y')}_" for e in entries]
        await message.answer(
            f"🔍 *Результаты:* _{query}_\n\n" + "\n".join(lines),
            reply_markup=journal_menu_keyboard(),
        )
    await state.clear()


@router.message(F.text == "📝 Журнал")
async def reply_journal(message: Message):
    await message.answer("📝 *Dev Journal*", reply_markup=journal_menu_keyboard())
