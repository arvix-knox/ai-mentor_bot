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
    task_priority_keyboard, task_deadline_keyboard,
    remind_time_keyboard, remind_exact_time_keyboard,
    confirm_keyboard,
)

router = Router()


class TaskStates(StatesGroup):
    waiting_title = State()
    waiting_priority = State()
    waiting_deadline = State()
    waiting_tags = State()
    waiting_edit = State()


def format_task(t) -> str:
    se = {"todo": "⬜ Ожидает", "in_progress": "🔄 В работе", "done": "✅ Готово"}.get(t.status, t.status)
    pe = {"low": "🟢 Low", "medium": "🟡 Medium", "high": "🟠 High", "critical": "🔴 Critical"}.get(t.priority, t.priority)
    text = f"📋 *{t.title}*\n\n📌 {se}\n⚡ {pe}\n"
    if t.deadline:
        dl = (t.deadline - date.today()).days
        if dl < 0:
            text += f"📅 {t.deadline} ⚠️ *Просрочено {abs(dl)}д*\n"
        elif dl == 0:
            text += f"📅 {t.deadline} 🔥 *Сегодня!*\n"
        else:
            text += f"📅 {t.deadline} ({dl}д)\n"
    if t.tags:
        text += f"🏷 {' '.join('#' + x for x in t.tags)}\n"
    text += f"\n🕐 {t.created_at.strftime('%d.%m.%Y %H:%M')}"
    if t.completed_at:
        text += f"\n✅ {t.completed_at.strftime('%d.%m.%Y %H:%M')}"
    return text


@router.message(Command("task"))
async def cmd_task(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("📋 *Задачи*", reply_markup=tasks_menu_keyboard())
        return
    action = parts[1].lower()
    svc = TaskService(session)
    if action == "add" and len(parts) > 2:
        data = _parse(parts[2])
        if not data["title"]:
            await message.answer("❌ Укажи название")
            return
        r = await svc.create_task(user_id=db_user.id, **data)
        await message.answer(f"✅ *{r['title']}*\n+5 XP ⭐", reply_markup=task_item_keyboard(r["task_id"]))
    elif action == "list":
        tasks = await svc.get_tasks(db_user.id)
        if tasks:
            await message.answer("📋 *Задачи:*", reply_markup=task_list_with_items(tasks))
        else:
            await message.answer("📋 Пусто", reply_markup=tasks_menu_keyboard())
    elif action == "done" and len(parts) > 2:
        try:
            tid = int(parts[2])
        except ValueError:
            await message.answer("❌ ID")
            return
        r = await svc.complete_task(db_user.id, tid)
        if r.get("error"):
            await message.answer(f"❌ {r['error']}")
        else:
            lm = f"\n🎉 *LEVEL UP!* {r['new_level']}!" if r.get("leveled_up") else ""
            await message.answer(f"✅ *{r['title']}*\n+{r['xp_earned']} XP ⭐{lm}", reply_markup=tasks_menu_keyboard())
    else:
        await message.answer("📋 *Задачи*", reply_markup=tasks_menu_keyboard())


def _parse(text):
    tags = re.findall(r"#(\w+)", text)
    c = re.sub(r"#\w+", "", text)
    p = "medium"
    pm = re.search(r"p:(\w+)", c)
    if pm:
        v = pm.group(1).lower()
        if v in ("low","medium","high","critical"):
            p = v
        c = c.replace(pm.group(0), "")
    dl = None
    dm = re.search(r"d:(\d{4}-\d{2}-\d{2})", c)
    if dm:
        try:
            dl = date.fromisoformat(dm.group(1))
        except ValueError:
            pass
        c = c.replace(dm.group(0), "")
    return {"title": c.strip(), "tags": tags or None, "priority": p, "deadline": dl}


@router.callback_query(F.data == "menu:tasks")
async def cb_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("📋 *Задачи*", reply_markup=tasks_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "task:add")
async def cb_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TaskStates.waiting_title)
    await state.update_data(task_tags=None, task_priority="medium", task_deadline=None)
    await callback.message.edit_text("➕ *Новая задача*\n\nОтправь название:")
    await callback.answer()


@router.message(TaskStates.waiting_title)
async def st_title(message: Message, state: FSMContext):
    title = message.text.strip()
    tags = re.findall(r"#(\w+)", title)
    title = re.sub(r"#\w+", "", title).strip()
    if not title:
        await message.answer("❌ Название")
        return
    await state.update_data(task_title=title, task_tags=tags or None)
    await state.set_state(TaskStates.waiting_priority)
    await message.answer("⚡ *Приоритет:*", reply_markup=task_priority_keyboard())


@router.callback_query(F.data.startswith("tpriority:"))
async def cb_priority(callback: CallbackQuery, state: FSMContext):
    p = callback.data.split(":")[1]
    await state.update_data(task_priority=p)
    await state.set_state(TaskStates.waiting_deadline)
    await callback.message.edit_text("📅 *Дедлайн:*", reply_markup=task_deadline_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("tdeadline:"))
async def cb_deadline(callback: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    val = callback.data.split(":")[1]
    dl = None if val == "none" else date.fromisoformat(val)
    await state.update_data(task_deadline=dl)
    data = await state.get_data()
    svc = TaskService(session)
    r = await svc.create_task(
        user_id=db_user.id, title=data["task_title"],
        priority=data["task_priority"], tags=data.get("task_tags"),
        deadline=data.get("task_deadline"),
    )
    dl_text = f"\n📅 {r['deadline']}" if r.get("deadline") else ""
    tg_text = f"\n🏷 {' '.join('#'+t for t in r['tags'])}" if r.get("tags") else ""
    await callback.message.edit_text(
        f"✅ Создано!\n\n*{r['title']}*\n⚡ {r['priority'].upper()}{dl_text}{tg_text}\n\n+5 XP ⭐",
        reply_markup=task_item_keyboard(r["task_id"]),
    )
    await callback.answer("Создано!")
    await state.clear()


@router.callback_query(F.data.startswith("task:list:"))
async def cb_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    ft = callback.data.split(":")[2]
    svc = TaskService(session)
    names = {"active": "Активные", "done": "Готовые", "overdue": "Просроченные", "all": "Все"}
    if ft == "active":
        tasks = await svc.get_tasks(db_user.id, status="todo")
    elif ft == "done":
        tasks = await svc.get_tasks(db_user.id, status="done")
    elif ft == "overdue":
        all_tasks = await svc.get_tasks(db_user.id)
        tasks = [t for t in all_tasks if t.deadline and t.deadline < date.today() and t.status in ("todo", "in_progress")]
    else:
        tasks = await svc.get_tasks(db_user.id)
    n = names.get(ft, "Все")
    if tasks:
        try:
            await callback.message.edit_text(f"📋 *{n}:*", reply_markup=task_list_with_items(tasks))
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text(f"📋 *{n}* — пусто", reply_markup=tasks_menu_keyboard())
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("task:view:"))
async def cb_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    tid = int(callback.data.split(":")[2])
    svc = TaskService(session)
    t = await svc.task_repo.get_by_id(tid)
    if not t or t.user_id != db_user.id:
        await callback.answer("Не найдено")
        return
    try:
        await callback.message.edit_text(format_task(t), reply_markup=task_item_keyboard(t.id, t.status))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("task:done:"))
async def cb_done(callback: CallbackQuery, session: AsyncSession, db_user: User):
    tid = int(callback.data.split(":")[2])
    svc = TaskService(session)
    r = await svc.complete_task(db_user.id, tid)
    if r.get("error"):
        await callback.answer(r["error"])
        return
    lm = f"\n🎉 *LEVEL UP!* {r['new_level']}!" if r.get("leveled_up") else ""
    try:
        await callback.message.edit_text(f"✅ *{r['title']}*\n+{r['xp_earned']} XP ⭐{lm}", reply_markup=tasks_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer("✅")


@router.callback_query(F.data.startswith("task:progress:"))
async def cb_progress(callback: CallbackQuery, session: AsyncSession, db_user: User):
    tid = int(callback.data.split(":")[2])
    svc = TaskService(session)
    t = await svc.task_repo.get_by_id(tid)
    if not t or t.user_id != db_user.id:
        await callback.answer("Нет")
        return
    await svc.task_repo.update(tid, status="in_progress")
    try:
        await callback.message.edit_text(f"🔄 В работе: *{t.title}*", reply_markup=task_item_keyboard(tid, "in_progress"))
    except TelegramBadRequest:
        pass
    await callback.answer("🔄")


@router.callback_query(F.data.startswith("task:reopen:"))
async def cb_reopen(callback: CallbackQuery, session: AsyncSession, db_user: User):
    tid = int(callback.data.split(":")[2])
    svc = TaskService(session)
    t = await svc.task_repo.get_by_id(tid)
    if not t or t.user_id != db_user.id:
        await callback.answer("Нет")
        return
    await svc.task_repo.update(tid, status="todo", completed_at=None)
    try:
        await callback.message.edit_text(f"↩️ Возвращено: *{t.title}*", reply_markup=task_item_keyboard(tid, "todo"))
    except TelegramBadRequest:
        pass
    await callback.answer("↩️")


@router.callback_query(F.data.startswith("task:del:"))
async def cb_del(callback: CallbackQuery):
    tid = int(callback.data.split(":")[2])
    try:
        await callback.message.edit_text("🗑 *Удалить?*", reply_markup=confirm_keyboard(f"task:del_yes:{tid}", "task:list:all"))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("task:del_yes:"))
async def cb_del_yes(callback: CallbackQuery, session: AsyncSession, db_user: User):
    tid = int(callback.data.split(":")[2])
    svc = TaskService(session)
    r = await svc.delete_task(db_user.id, tid)
    if r.get("error"):
        await callback.answer(r["error"])
        return
    try:
        await callback.message.edit_text(f"🗑 Удалено: *{r['title']}*", reply_markup=tasks_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("task:edit:"))
async def cb_edit(callback: CallbackQuery, state: FSMContext):
    tid = int(callback.data.split(":")[2])
    await state.set_state(TaskStates.waiting_edit)
    await state.update_data(edit_task_id=tid)
    await callback.message.edit_text("✏️ Отправь новое название\n(можно с #тегами p:приоритет):")
    await callback.answer()


@router.message(TaskStates.waiting_edit)
async def st_edit(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = await state.get_data()
    tid = data["edit_task_id"]
    parsed = _parse(message.text.strip())
    if not parsed["title"]:
        await message.answer("❌ Название")
        return
    svc = TaskService(session)
    upd = {"title": parsed["title"], "priority": parsed["priority"]}
    if parsed["tags"]:
        upd["tags"] = parsed["tags"]
    if parsed["deadline"]:
        upd["deadline"] = parsed["deadline"]
    await svc.task_repo.update(tid, **upd)
    await message.answer(f"✏️ *{parsed['title']}*", reply_markup=task_item_keyboard(tid))
    await state.clear()


@router.callback_query(F.data.startswith("task:remind:"))
async def cb_remind(callback: CallbackQuery):
    tid = int(callback.data.split(":")[2])
    await callback.message.edit_text("⏰ *Напоминание*\n\nКогда напомнить?", reply_markup=remind_time_keyboard(tid))
    await callback.answer()


@router.callback_query(F.data.startswith("tremind_period:"))
async def cb_remind_period(callback: CallbackQuery):
    parts = callback.data.split(":")
    tid = int(parts[1])
    period = parts[2]
    labels = {"morning": "🌅 Утро", "afternoon": "☀️ День", "evening": "🌙 Вечер"}
    await callback.message.edit_text(f"⏰ {labels.get(period, period)} — время:", reply_markup=remind_exact_time_keyboard(tid, period))
    await callback.answer()


@router.callback_query(F.data.startswith("tremind_set:"))
async def cb_remind_set(callback: CallbackQuery):
    parts = callback.data.split(":")
    tid = int(parts[1])
    time_val = parts[2]
    await callback.answer(f"⏰ Напоминание: {time_val}")
    try:
        await callback.message.edit_text(f"⏰ Напоминание установлено: *{time_val}*", reply_markup=task_item_keyboard(tid))
    except TelegramBadRequest:
        pass


@router.message(F.text == "📋 Задачи")
async def reply_tasks(message: Message, session: AsyncSession, db_user: User):
    svc = TaskService(session)
    tasks = await svc.get_tasks(db_user.id)
    if tasks:
        await message.answer("📋 *Задачи:*", reply_markup=task_list_with_items(tasks))
    else:
        await message.answer("📋 *Задачи*", reply_markup=tasks_menu_keyboard())
