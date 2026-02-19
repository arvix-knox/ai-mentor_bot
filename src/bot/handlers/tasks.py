import re
from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.task_service import TaskService
from src.services.gamification_service import GamificationService

router = Router()


def task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Done", callback_data=f"task_done:{task_id}"),
            InlineKeyboardButton(text="🗑 Delete", callback_data=f"task_del:{task_id}"),
        ]
    ])


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

    return {
        "title": title,
        "tags": tags if tags else None,
        "priority": priority,
        "deadline": deadline,
    }


@router.message(Command("task"))
async def cmd_task(message: Message, session: AsyncSession, db_user: User):
    text = message.text.strip()
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        await message.answer(
            "📋 *Task Manager*\n\n"
            "`/task add <title> #tags p:priority d:deadline`\n"
            "`/task list`\n"
            "`/task done <id>`\n"
            "`/task delete <id>`"
        )
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
        tags_text = f"\n🏷 Tags: {' '.join('#' + t for t in result['tags'])}" if result.get("tags") else ""

        await message.answer(
            f"✅ Задача создана: *{result['title']}*\n"
            f"⚡ Priority: {result['priority']}"
            f"{deadline_text}"
            f"{tags_text}\n"
            f"+5 XP ⭐",
            reply_markup=task_keyboard(result["task_id"]),
        )

    elif action == "list":
        tag_filter = parts[2].lstrip("#") if len(parts) > 2 else None
        tasks = await task_svc.get_tasks(db_user.id, tag=tag_filter)

        if not tasks:
            await message.answer("📋 Нет задач.")
            return

        status_emoji = {"todo": "⬜", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}
        priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}

        lines = []
        for t in tasks[:20]:
            line = (
                f"{status_emoji.get(t.status, '⬜')} "
                f"{priority_emoji.get(t.priority, '🟡')} "
                f"`#{t.id}` {t.title}"
            )
            if t.deadline:
                line += f" 📅{t.deadline}"
            lines.append(line)

        await message.answer("📋 *Твои задачи:*\n\n" + "\n".join(lines))

    elif action == "done" and len(parts) > 2:
        try:
            task_id = int(parts[2])
        except ValueError:
            await message.answer("❌ Неверный ID задачи")
            return

        result = await task_svc.complete_task(db_user.id, task_id)

        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
            return

        level_msg = ""
        if result.get("leveled_up"):
            level_msg = f"\n\n🎉 *LEVEL UP!* Ты теперь level {result['new_level']}!"

        await message.answer(
            f"✅ Задача выполнена: *{result['title']}*\n"
            f"+{result['xp_earned']} XP ⭐{level_msg}"
        )

    elif action == "delete" and len(parts) > 2:
        try:
            task_id = int(parts[2])
        except ValueError:
            await message.answer("❌ Неверный ID задачи")
            return

        result = await task_svc.delete_task(db_user.id, task_id)

        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
            return

        await message.answer(f"🗑 Задача удалена: *{result['title']}*")

    else:
        await message.answer("❌ Неизвестная команда. Используй /task для помощи.")


@router.callback_query(F.data.startswith("task_done:"))
async def callback_task_done(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[1])
    task_svc = TaskService(session)
    result = await task_svc.complete_task(db_user.id, task_id)

    if result.get("error"):
        await callback.answer(result["error"])
        return

    level_msg = ""
    if result.get("leveled_up"):
        level_msg = f"\n🎉 *LEVEL UP!* Level {result['new_level']}!"

    await callback.message.edit_text(
        f"✅ Выполнено: *{result['title']}*\n"
        f"+{result['xp_earned']} XP ⭐{level_msg}"
    )
    await callback.answer("Done!")


@router.callback_query(F.data.startswith("task_del:"))
async def callback_task_delete(callback: CallbackQuery, session: AsyncSession, db_user: User):
    task_id = int(callback.data.split(":")[1])
    task_svc = TaskService(session)
    result = await task_svc.delete_task(db_user.id, task_id)

    if result.get("error"):
        await callback.answer(result["error"])
        return

    await callback.message.edit_text(f"🗑 Удалено: *{result['title']}*")
    await callback.answer("Deleted!")