from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.habit_service import HabitService

router = Router()


def habits_list_keyboard(habits: list) -> InlineKeyboardMarkup:
    buttons = []
    for habit in habits:
        buttons.append([
            InlineKeyboardButton(
                text=f"{habit.emoji} {habit.name} (🔥{habit.current_streak})",
                callback_data=f"habit_check:{habit.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("habit"))
async def cmd_habit(message: Message, session: AsyncSession, db_user: User):
    text = message.text.strip()
    parts = text.split(maxsplit=2)

    if len(parts) < 2:
        await message.answer(
            "🔄 *Habit Tracker*\n\n"
            "`/habit add <название>` — создать привычку\n"
            "`/habit list` — список привычек\n"
            "`/habit check <id>` — отметить выполнение\n"
            "`/habit stats` — статистика за неделю\n"
            "`/habit delete <id>` — удалить привычку"
        )
        return

    action = parts[1].lower()
    habit_svc = HabitService(session)

    if action == "add" and len(parts) > 2:
        name = parts[2].strip()
        emoji = "✅"

        if len(name) >= 2 and not name[0].isalnum():
            emoji = name[0]
            name = name[1:].strip()
            if not name:
                await message.answer("❌ Укажи название привычки")
                return

        result = await habit_svc.create_habit(
            user_id=db_user.id,
            name=name,
            emoji=emoji,
        )

        await message.answer(
            f"{result['emoji']} Привычка создана: *{result['name']}*\n\n"
            f"Отмечай каждый день через /habit check {result['habit_id']}\n"
            f"Или используй /habit list для быстрой отметки"
        )

    elif action == "list":
        habits = await habit_svc.get_user_habits(db_user.id)

        if not habits:
            await message.answer(
                "🔄 У тебя пока нет привычек.\n\n"
                "Создай первую: `/habit add 📚 Читать документацию`"
            )
            return

        lines = []
        for h in habits:
            streak_display = f"🔥{h.current_streak}d" if h.current_streak > 0 else "0d"
            best_display = f"best: {h.best_streak}d"
            lines.append(
                f"{h.emoji} `#{h.id}` *{h.name}*\n"
                f"   Streak: {streak_display} | {best_display} | "
                f"Total: {h.total_completions}"
            )

        await message.answer(
            "🔄 *Твои привычки:*\n\n" + "\n\n".join(lines) + "\n\n"
            "Нажми кнопку для отметки ⬇️",
            reply_markup=habits_list_keyboard(habits),
        )

    elif action == "check" and len(parts) > 2:
        try:
            habit_id = int(parts[2])
        except ValueError:
            await message.answer("❌ Неверный ID привычки")
            return

        result = await habit_svc.log_completion(db_user.id, habit_id)

        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
            return

        if result.get("already_logged"):
            await message.answer(
                f"ℹ️ Уже отмечено сегодня! Streak: 🔥{result['streak']}d"
            )
            return

        milestone_msg = ""
        if result.get("streak_milestone"):
            milestone_msg = (
                f"\n\n🏆 *MILESTONE!* {result['streak_milestone']} дней подряд!"
            )

        await message.answer(
            f"✅ Привычка отмечена!\n\n"
            f"🔥 Streak: {result['streak']}d\n"
            f"🏆 Best: {result['best_streak']}d\n"
            f"📊 Total: {result['total_completions']}\n"
            f"+{result['xp_earned']} XP ⭐"
            f"{milestone_msg}"
        )

    elif action == "stats":
        perf = await habit_svc.get_weekly_performance(db_user.id)

        if not perf["habits"]:
            await message.answer("🔄 Нет привычек для статистики.")
            return

        lines = []
        for h in perf["habits"]:
            filled = int(h["rate"] * 10)
            bar = "▓" * filled + "░" * (10 - filled)
            lines.append(
                f"{h['emoji']} {h['name']}\n"
                f"   [{bar}] {h['rate']:.0%} "
                f"({h['completed']}/{h['possible']})\n"
                f"   🔥 Streak: {h['streak']}d | Best: {h['best_streak']}d"
            )

        await message.answer(
            f"📊 *Привычки за неделю*\n\n"
            + "\n\n".join(lines)
            + f"\n\n📈 Overall: {perf['overall_rate']:.0%} "
            f"({perf['total_completed']}/{perf['total_possible']})"
        )

    elif action == "delete" and len(parts) > 2:
        try:
            habit_id = int(parts[2])
        except ValueError:
            await message.answer("❌ Неверный ID привычки")
            return

        from src.repositories.habit_repo import HabitRepository
        habit_repo = HabitRepository(session)
        habit = await habit_repo.get_by_id(habit_id)

        if not habit or habit.user_id != db_user.id:
            await message.answer("❌ Привычка не найдена")
            return

        await habit_repo.update(habit_id, is_active=False)
        await message.answer(f"🗑 Привычка удалена: *{habit.name}*")

    else:
        await message.answer("❌ Неизвестная команда. Используй /habit для помощи.")


@router.callback_query(F.data.startswith("habit_check:"))
async def callback_habit_check(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_id = int(callback.data.split(":")[1])
    habit_svc = HabitService(session)

    result = await habit_svc.log_completion(db_user.id, habit_id)

    if result.get("error"):
        await callback.answer(result["error"])
        return

    if result.get("already_logged"):
        await callback.answer(f"Уже отмечено! Streak: 🔥{result['streak']}d")
        return

    milestone_msg = ""
    if result.get("streak_milestone"):
        milestone_msg = f"\n🏆 MILESTONE: {result['streak_milestone']}d!"

    await callback.answer(
        f"✅ Streak: 🔥{result['streak']}d | +{result['xp_earned']} XP"
    )

    habits = await habit_svc.get_user_habits(db_user.id)
    lines = []
    for h in habits:
        streak_display = f"🔥{h.current_streak}d" if h.current_streak > 0 else "0d"
        lines.append(
            f"{h.emoji} `#{h.id}` *{h.name}* — {streak_display}"
        )

    await callback.message.edit_text(
        "🔄 *Твои привычки:*\n\n" + "\n".join(lines)
        + f"{milestone_msg}\n\nНажми кнопку для отметки ⬇️",
        reply_markup=habits_list_keyboard(habits),
    )