from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.habit_service import HabitService
from src.repositories.habit_repo import HabitRepository
from src.bot.keyboards.inline import (
    habits_menu_keyboard, habits_check_keyboard,
    habit_manage_keyboard, habit_delete_confirm_keyboard,
    back_keyboard,
)

router = Router()


class HabitStates(StatesGroup):
    waiting_name = State()


@router.message(Command("habit"))
async def cmd_habit(message: Message, session: AsyncSession, db_user: User):
    text = message.text.strip()
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("🔄 *Трекер привычек*", reply_markup=habits_menu_keyboard())
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
            await message.answer("❌ Укажи название")
            return
        result = await habit_svc.create_habit(user_id=db_user.id, name=name, emoji=emoji)
        await message.answer(f"{result['emoji']} Создано: *{result['name']}*", reply_markup=habits_menu_keyboard())
    elif action == "check" and len(parts) > 2:
        try:
            habit_id = int(parts[2])
        except ValueError:
            await message.answer("❌ Неверный ID")
            return
        result = await habit_svc.log_completion(db_user.id, habit_id)
        if result.get("error"):
            await message.answer(f"❌ {result['error']}")
            return
        if result.get("already_logged"):
            await message.answer(f"ℹ️ Уже отмечено! 🔥{result['streak']}d")
            return
        milestone = f"\n🏆 *{result['streak_milestone']}d MILESTONE!*" if result.get("streak_milestone") else ""
        await message.answer(
            f"✅ 🔥 *{result['streak']}d* streak\n+{result['xp_earned']} XP ⭐{milestone}",
            reply_markup=habits_menu_keyboard(),
        )
    elif action == "list":
        habits = await habit_svc.get_user_habits(db_user.id)
        if habits:
            await message.answer("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))
        else:
            await message.answer("🔄 Пусто. Создай: `/habit add 📚 Читать`", reply_markup=habits_menu_keyboard())
    else:
        await message.answer("🔄 *Трекер привычек*", reply_markup=habits_menu_keyboard())


@router.callback_query(F.data == "menu:habits")
async def cb_habits_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🔄 *Трекер привычек*", reply_markup=habits_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "habit:add")
async def cb_habit_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HabitStates.waiting_name)
    await callback.message.edit_text(
        "➕ *Новая привычка*\n\n"
        "Отправь название (эмоджи в начале = иконка):\n"
        "• `📚 Читать 30 минут`\n"
        "• `💻 Писать код`\n"
        "• `🏃 Тренировка`"
    )
    await callback.answer()


@router.message(HabitStates.waiting_name)
async def habit_name_input(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    name = message.text.strip()
    emoji = "✅"
    if len(name) >= 2 and not name[0].isalnum():
        emoji = name[0]
        name = name[1:].strip()
    if not name:
        await message.answer("❌ Укажи название")
        return
    habit_svc = HabitService(session)
    result = await habit_svc.create_habit(user_id=db_user.id, name=name, emoji=emoji)
    await message.answer(f"{result['emoji']} Создано: *{result['name']}*\n\nОтмечай каждый день!", reply_markup=habits_menu_keyboard())
    await state.clear()


@router.callback_query(F.data == "habit:list")
async def cb_habit_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_svc = HabitService(session)
    habits = await habit_svc.get_user_habits(db_user.id)
    if not habits:
        try:
            await callback.message.edit_text("🔄 Нет привычек", reply_markup=habits_menu_keyboard())
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("habit:check:"))
async def cb_habit_check(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_id = int(callback.data.split(":")[2])
    habit_svc = HabitService(session)
    result = await habit_svc.log_completion(db_user.id, habit_id)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    if result.get("already_logged"):
        await callback.answer(f"Уже отмечено! 🔥{result['streak']}d")
        return
    milestone = f" | 🏆 {result['streak_milestone']}d!" if result.get("streak_milestone") else ""
    await callback.answer(f"✅ 🔥{result['streak']}d +{result['xp_earned']}XP{milestone}")
    habits = await habit_svc.get_user_habits(db_user.id)
    try:
        await callback.message.edit_text("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "habit:stats")
async def cb_habit_stats(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_svc = HabitService(session)
    perf = await habit_svc.get_weekly_performance(db_user.id)
    if not perf["habits"]:
        try:
            await callback.message.edit_text("📊 Нет данных", reply_markup=habits_menu_keyboard())
        except TelegramBadRequest:
            pass
        await callback.answer()
        return
    lines = []
    for h in perf["habits"]:
        filled = int(h["rate"] * 10)
        bar = "▓" * filled + "░" * (10 - filled)
        lines.append(
            f"{h['emoji']} *{h['name']}*\n"
            f"   [{bar}] {h['rate']:.0%} ({h['completed']}/{h['possible']})\n"
            f"   🔥 {h['streak']}d | 🏆 best {h['best_streak']}d"
        )
    try:
        await callback.message.edit_text(
            f"📊 *Привычки за неделю*\n\n" + "\n\n".join(lines) + f"\n\n📈 Итого: *{perf['overall_rate']:.0%}*",
            reply_markup=habits_menu_keyboard(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "habit:manage")
async def cb_habit_manage(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_svc = HabitService(session)
    habits = await habit_svc.get_user_habits(db_user.id)
    if not habits:
        try:
            await callback.message.edit_text("🔄 Нет привычек", reply_markup=habits_menu_keyboard())
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text("🗑 *Управление привычками*\n\nНажми 🗑 чтобы удалить:", reply_markup=habit_manage_keyboard(habits))
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("habit:del:"))
async def cb_habit_del(callback: CallbackQuery):
    habit_id = int(callback.data.split(":")[2])
    try:
        await callback.message.edit_text("🗑 *Удалить привычку?*", reply_markup=habit_delete_confirm_keyboard(habit_id))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("habit:del_yes:"))
async def cb_habit_del_confirm(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_id = int(callback.data.split(":")[2])
    habit_repo = HabitRepository(session)
    habit = await habit_repo.get_by_id(habit_id)
    if not habit or habit.user_id != db_user.id:
        await callback.answer("Не найдено")
        return
    await habit_repo.update(habit_id, is_active=False)
    try:
        await callback.message.edit_text(f"🗑 Удалено: *{habit.name}*", reply_markup=habits_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("habit:info:"))
async def cb_habit_info(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_id = int(callback.data.split(":")[2])
    habit_repo = HabitRepository(session)
    habit = await habit_repo.get_by_id(habit_id)
    if not habit or habit.user_id != db_user.id:
        await callback.answer("Не найдено")
        return
    text = (
        f"{habit.emoji} *{habit.name}*\n\n"
        f"🔥 Streak: *{habit.current_streak}d*\n"
        f"🏆 Best: *{habit.best_streak}d*\n"
        f"📊 Total: *{habit.total_completions}*\n"
        f"⭐ XP за отметку: *{habit.xp_per_completion}*"
    )
    try:
        await callback.message.edit_text(text, reply_markup=back_keyboard("habit:manage"))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(F.text == "🔄 Привычки")
async def reply_habits(message: Message, session: AsyncSession, db_user: User):
    habit_svc = HabitService(session)
    habits = await habit_svc.get_user_habits(db_user.id)
    if habits:
        await message.answer("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))
    else:
        await message.answer("🔄 *Трекер привычек*", reply_markup=habits_menu_keyboard())
