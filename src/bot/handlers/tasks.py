import re
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.task_service import TaskService
from src.services.gamification_service import GamificationService
from src.bot.keyboards.inline import tasks_menu_keyboard, task_item_keyboard, back_to_menu_keyboard

router = Router()


class TaskStates(StatesGroup):
    waiting_task_input = State()


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

    title = text_clean.strip()
    return {"title": title, "tags": tags if tags else None, "priority": priority, "deadline": deadline}


def format_task_list(tasks: list) -> str:
    if not tasks:
        return "📋 Нет задач"
    status_emoji = {"todo": "⬜", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}
    priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
    lines = []
    for t in tasks[:15]:
        line = (
            f"{status_emoji.get(t.status, '⬜')} "
            f"{priority_emoji.get(t.priority, '🟡')} "
            f"`#{t.id}` *{t.title}*"
        )
        if t.deadline:
            line += f" 📅 {t.deadline}"
        if t.tags:
            line += f"\n   🏷 {' '.join('#' + tag for tag in t.tags)}"
        lines.append(line)
    return "\n\n".join(lines)


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
            await message.answer("❌ Укажи название задачи")
            return
        result = await task_svc.create_task(user_id=db_user.id, **task_data)
        deadline_text = f"\n📅 Deadline: {result['deadline']}" if result.get("deadline") else ""
        tags_text = f"\n🏷 {' '.join('#' + t for t in result['tags'])}" if result.get("tags") else ""
        await message.answer(
            f"✅ Задача создана!\n\n"
            f"*{result['title']}*\n"
            f"⚡ {result['priority'].upper()}"
            f"{deadline_text}{tags_text}\n\n"
            f"+5 XP ⭐",
            reply_markup=task_item_keyboard(result["task_id"]),
        )

    elif action == "list":
        tag_filter = parts[2].lstrip("#") if len(parts) > 2 else None
        tasks = await task_svc.get_tasks(db_user.id, tag=tag_filter)
        text = format_task_list(tasks)
        await message.answer(f"📋 *Твои задачи:*\n\n{text}", reply_markup=tasks_menu_keyboard())

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
        level_msg = f"\n\n🎉 *LEVEL UP!* Level {result['new_level']}!" if result.get("leveled_up") else ""
        await message.answer(
            f"✅ Выполнено: *{result['title']}*\n+{result['xp_earned']} XP ⭐{level_msg}",
            reply_markup=tasks_menu_keyboard(),
        )

    elif action == "delete" and len(parts) > 2:
        try:
            task_id = int(parts[2])
        except ValueError:
            await message.answer("❌ Неверный ID")
            return
        result = await task_svc.delete_task(db_user.id, task_id)
        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
            return
        await message.answer(f"🗑 Удалено: *{result['title']}*", reply_markup=tasks_menu_keyboard())

    else:
        await message.answer("📋 *Менеджер задач*", reply_markup=tasks_menu_keyboard())


@router.callback_query(F.data == "menu:tasks")
async def callback_tasks_menu(callback: CallbackQuery):
    await callback.message.edit_text("📋 *Менеджер задач*", reply_markup=tasks_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "task:add")
async def callback_task_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TaskStates.waiting_task_input)
    await callback.message.edit_text(
        "➕ *Новая задача*\n\n"
        "Отправь задачу в формате:\n"
        "`Название #тег p:high d:2025-12-31`\n\n"
        "Примеры:\n"
        "`Изучить async Python #python p:high`\n"
        "`Написать тесты #testing d:2025-07-25`\n"
        "`Прочитать документацию`",
    )
    await callback.answer()


@router.message(TaskStates.waiting_task_input)
async def task_input_received(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    task_data = parse_task_input(message.text.strip())
    if not task_data["title"]:
        await message.answer("❌ Укажи название задачи")
        return
    task_svc = TaskService(session)
    result = await task_svc.create_task(user_id=db_user.id, **task_data)
    deadline_text = f"\n📅 Deadline: {result['deadline']}" if result.get("deadline") else ""
    tags_text = f"\n🏷 {' '.join('#' + t for t in result['tags'])}" if result.get("tags") else ""
    await message.answer(
        f"✅ Задача создана!\n\n"
        f"*{result['title']}*\n"
        f"⚡ {result['priority'].upper()}"
        f"{deadline_text}{tags_text}\n\n"
        f"+5 XP ⭐",
        reply_markup=task_item_keyboard(result["task_id"]),
    )
    await state.clear()


@router.callback_query(F.data.startswith("task:list:"))
async def callback_task_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    filter_type = callback.data.split(":")[2]
    task_svc = TaskService(session)
    if filter_type == "active":
        tasks = await task_svc.get_tasks(db_user.id, status="todo")
    elif filter_type == "done":
        tasks = await task_svc.get_tasks(db_user.id, status="done")
    else:
        tasks = await task_svc.get_tasks(db_user.id)
    text = format_task_list(tasks)
    await callback.message.edit_text(f"📋 *Задачи:*\n\n{text}", reply_markup=tasks_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("task:done:"))
async def callback_task_done(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    task_svc = TaskService(session)
    result = await task_svc.complete_task(db_user.id, task_id)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    level_msg = f"\n🎉 *LEVEL UP!* Level {result['new_level']}!" if result.get("leveled_up") else ""
    await callback.message.edit_text(
        f"✅ *{result['title']}*\n+{result['xp_earned']} XP ⭐{level_msg}",
        reply_markup=tasks_menu_keyboard(),
    )
    await callback.answer("Done!")


@router.callback_query(F.data.startswith("task:del:"))
async def callback_task_delete(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[2])
    task_svc = TaskService(session)
    result = await task_svc.delete_task(db_user.id, task_id)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    await callback.message.edit_text(f"🗑 Удалено: *{result['title']}*", reply_markup=tasks_menu_keyboard())
    await callback.answer("Deleted!")


@router.message(F.text == "📋 Задачи")
async def reply_tasks(message: Message):
    await message.answer("📋 *Менеджер задач*", reply_markup=tasks_menu_keyboard())
