import re
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.task_service import TaskService
from src.bot.keyboards.inline import (
    tasks_menu_keyboard, task_item_keyboard, task_list_with_items,
    back_keyboard, confirm_delete_keyboard,
)

router = Router()


class TaskStates(StatesGroup):
    waiting_input = State()
    waiting_edit = State()


def parse_task_input(text: str) -> dict:
    tags = re.findall(r"#(\w+)", text)
    text_clean = re.sub(r"#\w+", "", text)
    priority = "medium"
    p_match = re.search(r"p:(\w+)", text_clean)
    if p_match:
        p = p_match.group(1).lower()
        if p in ("low", "medium", "high", "critical"):
            priority = p
        text_clean = text_clean.replace(p_match.group(0), "")
    deadline = None
    d_match = re.search(r"d:(\d{4}-\d{2}-\d{2})", text_clean)
    if d_match:
        try:
            deadline = date.fromisoformat(d_match.group(1))
        except ValueError:
            pass
        text_clean = text_clean.replace(d_match.group(0), "")
    return {"title": text_clean.strip(), "tags": tags or None, "priority": priority, "deadline": deadline}


def format_task_detail(t) -> str:
    status_emoji = {"todo": "⬜ Ожидает", "in_progress": "🔄 В работе", "done": "✅ Готово", "cancelled": "❌ Отменено"}
    priority_emoji = {"low": "🟢 Low", "medium": "🟡 Medium", "high": "🟠 High", "critical": "🔴 Critical"}
    text = (
        f"📋 *{t.title}*\n\n"
        f"Статус: {status_emoji.get(t.status, t.status)}\n"
        f"Приоритет: {priority_emoji.get(t.priority, t.priority)}\n"
    )
    if t.deadline:
        days_left = (t.deadline - date.today()).days
        if days_left < 0:
            text += f"📅 Дедлайн: {t.deadline} ⚠️ *Просрочено на {abs(days_left)}д*\n"
        elif days_left == 0:
            text += f"📅 Дедлайн: {t.deadline} 🔥 *Сегодня!*\n"
        else:
            text += f"📅 Дедлайн: {t.deadline} ({days_left}д)\n"
    if t.tags:
        text += f"🏷 {' '.join('#' + tag for tag in t.tags)}\n"
    if t.description:
        text += f"\n📝 {t.description}\n"
    text += f"\n🕐 Создано: {t.created_at.strftime('%d.%m.%Y %H:%M')}"
    if t.completed_at:
        text += f"\n✅ Завершено: {t.completed_at.strftime('%d.%m.%Y %H:%M')}"
    return text


@router.message(Command("task"))
async def cmd_task(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    text = message.text.strip()
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("📋 *Менеджер задач*", reply_markup=tasks_menu_keyboard())
        return
    action = parts[1].lower()
    task_svc = TaskService(session)
    if action == "add" and len(parts) > 2:
        task_data = parse_task_input(parts[2])
        if not task_data["title"]:
            await message.answer("❌ Укажи название")
            return
        result = await task_svc.create_task(user_id=db_user.id, **task_data)
        await message.answer(
            f"✅ Создано: *{result['title']}*\n+5 XP ⭐",
            reply_markup=task_item_keyboard(result["task_id"]),
        )
    elif action == "list":
        tasks = await task_svc.get_tasks(db_user.id)
        if not tasks:
            await message.answer("📋 Нет задач", reply_markup=tasks_menu_keyboard())
        else:
            await message.answer("📋 *Задачи* — нажми для деталей:", reply_markup=task_list_with_items(tasks))
    elif action == "done" and len(parts) > 2:
        try:
            task_id = int(parts[2])
        except ValueError:
            await message.answer("❌ Неверный ID")
            return
        result = await task_svc.complete_task(db_user.id, task_id)
        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
            return
        level_msg = f"\n🎉 *LEVEL UP!* Level {result['new_level']}!" if result.get("leveled_up") else ""
        await message.answer(f"✅ *{result['title']}*\n+{result['xp_earned']} XP ⭐{level_msg}", reply_markup=tasks_menu_keyboard())
    else:
        await message.answer("📋 *Менеджер задач*", reply_markup=tasks_menu_keyboard())


@router.callback_query(F.data == "menu:tasks")
async def cb_tasks_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("📋 *Менеджер задач*", reply_markup=tasks_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "task:add")
async def cb_task_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TaskStates.waiting_input)
    await callback.message.edit_text(
        "➕ *Новая задача*\n\n"
        "Формат: `Название #тег p:high d:2025-12-31`\n\n"
        "Примеры:\n"
        "• `Изучить FastAPI #python p:high`\n"
        "• `Написать тесты #testing d:2025-08-01`\n"
        "• `Рефакторинг модуля`"
    )
    await callback.answer()


@router.message(TaskStates.waiting_input)
async def task_input(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = parse_task_input(message.text.strip())
    if not data["title"]:
        await message.answer("❌ Укажи название")
        return
    task_svc = TaskService(session)
    result = await task_svc.create_task(user_id=db_user.id, **data)
    deadline_text = f"\n📅 {result['deadline']}" if result.get("deadline") else ""
    tags_text = f"\n🏷 {' '.join('#' + t for t in result['tags'])}" if result.get("tags") else ""
    await message.answer(
        f"✅ Создано!\n\n*{result['title']}*\n⚡ {result['priority'].upper()}{deadline_text}{tags_text}\n\n+5 XP ⭐",
        reply_markup=task_item_keyboard(result["task_id"]),
    )
    await state.clear()


@router.callback_query(F.data.startswith("task:list:"))
async def cb_task_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    filter_type = callback.data.split(":")[2]
    task_svc = TaskService(session)
    names = {"active": "Активные", "done": "Выполненные", "all": "Все"}
    if filter_type == "active":
        tasks = await task_svc.get_tasks(db_user.id, status="todo")
    elif filter_type == "done":
        tasks = await task_svc.get_tasks(db_user.id, status="done")
    else:
        tasks = await task_svc.get_tasks(db_user.id)
    name = names.get(filter_type, "Все")
    if not tasks:
        try:
            await callback.message.edit_text(f"📋 *{name}* — пусто", reply_markup=tasks_menu_keyboard())
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text(f"📋 *{name}* — нажми для деталей:", reply_markup=task_list_with_items(tasks))
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("task:view:"))
async def cb_task_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    task_svc = TaskService(session)
    task = await task_svc.task_repo.get_by_id(task_id)
    if not task or task.user_id != db_user.id:
        await callback.answer("Задача не найдена")
        return
    text = format_task_detail(task)
    try:
        await callback.message.edit_text(text, reply_markup=task_item_keyboard(task.id, task.status))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("task:done:"))
async def cb_task_done(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    task_svc = TaskService(session)
    result = await task_svc.complete_task(db_user.id, task_id)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    level_msg = f"\n🎉 *LEVEL UP!* Level {result['new_level']}!" if result.get("leveled_up") else ""
    try:
        await callback.message.edit_text(
            f"✅ Выполнено!\n\n*{result['title']}*\n+{result['xp_earned']} XP ⭐{level_msg}",
            reply_markup=tasks_menu_keyboard(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("✅ Выполнено!")


@router.callback_query(F.data.startswith("task:progress:"))
async def cb_task_progress(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    task_svc = TaskService(session)
    task = await task_svc.task_repo.get_by_id(task_id)
    if not task or task.user_id != db_user.id:
        await callback.answer("Не найдено")
        return
    await task_svc.task_repo.update(task_id, status="in_progress")
    try:
        await callback.message.edit_text(
            f"🔄 В работе: *{task.title}*",
            reply_markup=task_item_keyboard(task_id, "in_progress"),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("🔄 В работе")


@router.callback_query(F.data.startswith("task:reopen:"))
async def cb_task_reopen(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    task_svc = TaskService(session)
    task = await task_svc.task_repo.get_by_id(task_id)
    if not task or task.user_id != db_user.id:
        await callback.answer("Не найдено")
        return
    await task_svc.task_repo.update(task_id, status="todo", completed_at=None)
    try:
        await callback.message.edit_text(
            f"↩️ Возвращено: *{task.title}*",
            reply_markup=task_item_keyboard(task_id, "todo"),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("↩️ Возвращено")


@router.callback_query(F.data.startswith("task:del:"))
async def cb_task_del(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    try:
        await callback.message.edit_text(
            "🗑 *Удалить задачу?*",
            reply_markup=confirm_delete_keyboard(f"task:del_yes:{task_id}", "task:list:all"),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("task:del_yes:"))
async def cb_task_del_confirm(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    task_svc = TaskService(session)
    result = await task_svc.delete_task(db_user.id, task_id)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    try:
        await callback.message.edit_text(f"🗑 Удалено: *{result['title']}*", reply_markup=tasks_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("task:edit:"))
async def cb_task_edit(callback: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    task_id = int(callback.data.split(":")[2])
    await state.set_state(TaskStates.waiting_edit)
    await state.update_data(edit_task_id=task_id)
    await callback.message.edit_text(
        "✏️ *Редактирование*\n\nОтправь новое название задачи\n(можно с #тегами и p:приоритет):"
    )
    await callback.answer()


@router.message(TaskStates.waiting_edit)
async def task_edit_input(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = await state.get_data()
    task_id = data["edit_task_id"]
    parsed = parse_task_input(message.text.strip())
    if not parsed["title"]:
        await message.answer("❌ Укажи название")
        return
    task_svc = TaskService(session)
    update_data = {"title": parsed["title"], "priority": parsed["priority"]}
    if parsed["tags"]:
        update_data["tags"] = parsed["tags"]
    if parsed["deadline"]:
        update_data["deadline"] = parsed["deadline"]
    await task_svc.task_repo.update(task_id, **update_data)
    await message.answer(f"✏️ Обновлено: *{parsed['title']}*", reply_markup=task_item_keyboard(task_id))
    await state.clear()


@router.message(F.text == "📋 Задачи")
async def reply_tasks(message: Message, session: AsyncSession, db_user: User):
    task_svc = TaskService(session)
    tasks = await task_svc.get_tasks(db_user.id)
    if tasks:
        await message.answer("📋 *Задачи:*", reply_markup=task_list_with_items(tasks))
    else:
        await message.answer("📋 *Менеджер задач*", reply_markup=tasks_menu_keyboard())
