from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.habit_service import HabitService
from src.bot.keyboards.inline import habits_menu_keyboard, habits_check_keyboard, back_to_menu_keyboard

router = Router()


class HabitStates(StatesGroup):
    waiting_habit_name = State()


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
            await message.answer("❌ Укажи название привычки")
            return
        result = await habit_svc.create_habit(user_id=db_user.id, name=name, emoji=emoji)
        await message.answer(
            f"{result['emoji']} Привычка создана: *{result['name']}*\n\n"
            f"Отмечай выполнение каждый день!",
            reply_markup=habits_menu_keyboard(),
        )

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
        milestone_msg = f"\n\n🏆 *MILESTONE!* {result['streak_milestone']} дней!" if result.get("streak_milestone") else ""
        await message.answer(
            f"✅ Отмечено!\n\n"
            f"🔥 Streak: *{result['streak']}d*\n"
            f"🏆 Best: {result['best_streak']}d\n"
            f"+{result['xp_earned']} XP ⭐{milestone_msg}",
            reply_markup=habits_menu_keyboard(),
        )

    elif action == "list":
        habits = await habit_svc.get_user_habits(db_user.id)
        if not habits:
            await message.answer("🔄 Нет привычек. Создай: `/habit add 📚 Читать`", reply_markup=habits_menu_keyboard())
            return
        await message.answer("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))

    else:
        await message.answer("🔄 *Трекер привычек*", reply_markup=habits_menu_keyboard())


@router.callback_query(F.data == "menu:habits")
async def callback_habits_menu(callback: CallbackQuery):
    await callback.message.edit_text("🔄 *Трекер привычек*", reply_markup=habits_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "habit:add")
async def callback_habit_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HabitStates.waiting_habit_name)
    await callback.message.edit_text(
        "➕ *Новая привычка*\n\n"
        "Отправь название:\n"
        "`📚 Читать 30 минут`\n"
        "`💪 Тренировка`\n"
        "`💻 Писать код`\n\n"
        "Первый символ-эмоджи станет иконкой привычки",
    )
    await callback.answer()


@router.message(HabitStates.waiting_habit_name)
async def habit_name_received(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
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
    await message.answer(
        f"{result['emoji']} Создано: *{result['name']}*",
        reply_markup=habits_menu_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data == "habit:list")
async def callback_habit_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_svc = HabitService(session)
    habits = await habit_svc.get_user_habits(db_user.id)
    if not habits:
        await callback.message.edit_text("🔄 Нет привычек", reply_markup=habits_menu_keyboard())
        await callback.answer()
        return
    await callback.message.edit_text("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))
    await callback.answer()


@router.callback_query(F.data.startswith("habit:check:"))
async def callback_habit_check(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_id = int(callback.data.split(":")[2])
    habit_svc = HabitService(session)
    result = await habit_svc.log_completion(db_user.id, habit_id)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    if result.get("already_logged"):
        await callback.answer(f"Уже отмечено! 🔥{result['streak']}d")
        return
    await callback.answer(f"✅ 🔥{result['streak']}d | +{result['xp_earned']} XP")
    habits = await habit_svc.get_user_habits(db_user.id)
    await callback.message.edit_text("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))


@router.callback_query(F.data == "habit:stats")
async def callback_habit_stats(callback: CallbackQuery, session: AsyncSession, db_user: User):
    habit_svc = HabitService(session)
    perf = await habit_svc.get_weekly_performance(db_user.id)
    if not perf["habits"]:
        await callback.message.edit_text("📊 Нет данных", reply_markup=habits_menu_keyboard())
        await callback.answer()
        return
    lines = []
    for h in perf["habits"]:
        filled = int(h["rate"] * 10)
        bar = "▓" * filled + "░" * (10 - filled)
        lines.append(
            f"{h['emoji']} *{h['name']}*\n"
            f"   [{bar}] {h['rate']:.0%} ({h['completed']}/{h['possible']})\n"
            f"   🔥 {h['streak']}d | 🏆 {h['best_streak']}d"
        )
    await callback.message.edit_text(
        f"📊 *Привычки за неделю*\n\n"
        + "\n\n".join(lines)
        + f"\n\n📈 Итого: *{perf['overall_rate']:.0%}*",
        reply_markup=habits_menu_keyboard(),
    )
    await callback.answer()


@router.message(F.text == "🔄 Привычки")
async def reply_habits(message: Message, session: AsyncSession, db_user: User):
    habit_svc = HabitService(session)
    habits = await habit_svc.get_user_habits(db_user.id)
    if habits:
        await message.answer("🔄 *Отметь привычки:*", reply_markup=habits_check_keyboard(habits))
    else:
        await message.answer("🔄 *Трекер привычек*", reply_markup=habits_menu_keyboard())
