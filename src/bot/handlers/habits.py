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
    habit_schedule_keyboard, back_keyboard,
)

router = Router()

SCHEDULE_NAMES = {127: "Каждый день", 31: "Будни", 96: "Выходные", 85: "Через день"}


class HabitStates(StatesGroup):
    waiting_name = State()


@router.message(Command("habit"))
async def cmd(message: Message, session: AsyncSession, db_user: User):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("🔄 *Привычки*", reply_markup=habits_menu_keyboard())
        return
    a = parts[1].lower()
    svc = HabitService(session)
    if a == "add" and len(parts) > 2:
        n = parts[2].strip()
        e = "✅"
        if len(n) >= 2 and not n[0].isalnum():
            e = n[0]; n = n[1:].strip()
        if not n:
            await message.answer("❌ Название")
            return
        r = await svc.create_habit(user_id=db_user.id, name=n, emoji=e)
        await message.answer(f"{r['emoji']} *{r['name']}*", reply_markup=habits_menu_keyboard())
    elif a == "list":
        h = await svc.get_user_habits(db_user.id)
        if h:
            await message.answer("🔄 *Отметь:*", reply_markup=habits_check_keyboard(h))
        else:
            await message.answer("🔄 Пусто", reply_markup=habits_menu_keyboard())
    elif a == "check" and len(parts) > 2:
        try:
            hid = int(parts[2])
        except ValueError:
            await message.answer("❌ ID")
            return
        r = await svc.log_completion(db_user.id, hid)
        if r.get("error"):
            await message.answer(f"❌ {r['error']}")
        elif r.get("already_logged"):
            await message.answer(f"ℹ️ 🔥{r['streak']}d")
        else:
            ms = f"\n🏆 *{r['streak_milestone']}d!*" if r.get("streak_milestone") else ""
            await message.answer(f"✅ 🔥*{r['streak']}d*\n+{r['xp_earned']} XP ⭐{ms}", reply_markup=habits_menu_keyboard())
    else:
        await message.answer("🔄 *Привычки*", reply_markup=habits_menu_keyboard())


@router.callback_query(F.data == "menu:habits")
async def cb_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🔄 *Привычки*", reply_markup=habits_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "habit:add")
async def cb_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HabitStates.waiting_name)
    await callback.message.edit_text("➕ *Новая привычка*\n\nОтправь название\n(эмоджи = иконка):\n`📚 Читать`")
    await callback.answer()


@router.message(HabitStates.waiting_name)
async def st_name(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    n = message.text.strip()
    e = "✅"
    if len(n) >= 2 and not n[0].isalnum():
        e = n[0]; n = n[1:].strip()
    if not n:
        await message.answer("❌ Название")
        return
    svc = HabitService(session)
    r = await svc.create_habit(user_id=db_user.id, name=n, emoji=e)
    await message.answer(f"{r['emoji']} *{r['name']}* создано!", reply_markup=habits_menu_keyboard())
    await state.clear()


@router.callback_query(F.data == "habit:list")
async def cb_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    svc = HabitService(session)
    h = await svc.get_user_habits(db_user.id)
    if h:
        try:
            await callback.message.edit_text("🔄 *Отметь:*", reply_markup=habits_check_keyboard(h))
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text("🔄 Пусто", reply_markup=habits_menu_keyboard())
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("habit:check:"))
async def cb_check(callback: CallbackQuery, session: AsyncSession, db_user: User):
    hid = int(callback.data.split(":")[2])
    svc = HabitService(session)
    r = await svc.log_completion(db_user.id, hid)
    if r.get("error"):
        await callback.answer(r["error"])
        return
    if r.get("already_logged"):
        await callback.answer(f"Уже! 🔥{r['streak']}d")
        return
    ms = f" 🏆{r['streak_milestone']}d!" if r.get("streak_milestone") else ""
    await callback.answer(f"✅ 🔥{r['streak']}d +{r['xp_earned']}XP{ms}")
    h = await svc.get_user_habits(db_user.id)
    try:
        await callback.message.edit_text("🔄 *Отметь:*", reply_markup=habits_check_keyboard(h))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "habit:stats")
async def cb_stats(callback: CallbackQuery, session: AsyncSession, db_user: User):
    svc = HabitService(session)
    p = await svc.get_weekly_performance(db_user.id)
    if not p["habits"]:
        try:
            await callback.message.edit_text("📊 Нет данных", reply_markup=habits_menu_keyboard())
        except TelegramBadRequest:
            pass
        await callback.answer()
        return
    lines = []
    for h in p["habits"]:
        f = int(h["rate"] * 10)
        b = "▓" * f + "░" * (10 - f)
        lines.append(f"{h['emoji']} *{h['name']}*\n   [{b}] {h['rate']:.0%}\n   🔥{h['streak']}d 🏆{h['best_streak']}d")
    try:
        await callback.message.edit_text(
            f"📊 *Неделя*\n\n" + "\n\n".join(lines) + f"\n\n📈 *{p['overall_rate']:.0%}*",
            reply_markup=habits_menu_keyboard(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "habit:manage")
async def cb_manage(callback: CallbackQuery, session: AsyncSession, db_user: User):
    svc = HabitService(session)
    h = await svc.get_user_habits(db_user.id)
    if h:
        try:
            await callback.message.edit_text("🗑 *Управление*", reply_markup=habit_manage_keyboard(h))
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text("🔄 Пусто", reply_markup=habits_menu_keyboard())
        except TelegramBadRequest:
            pass
    await callback.answer()


@router.callback_query(F.data.startswith("habit:info:"))
async def cb_info(callback: CallbackQuery, session: AsyncSession, db_user: User):
    hid = int(callback.data.split(":")[2])
    repo = HabitRepository(session)
    h = await repo.get_by_id(hid)
    if not h or h.user_id != db_user.id:
        await callback.answer("Нет")
        return
    sn = SCHEDULE_NAMES.get(h.schedule_mask, "Пользовательский")
    text = (
        f"{h.emoji} *{h.name}*\n\n"
        f"🔥 Streak: *{h.current_streak}d*\n"
        f"🏆 Best: *{h.best_streak}d*\n"
        f"📊 Total: *{h.total_completions}*\n"
        f"📅 График: {sn}\n"
        f"⭐ XP: {h.xp_per_completion}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=habit_schedule_keyboard(hid))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("hsched:"))
async def cb_schedule(callback: CallbackQuery, session: AsyncSession, db_user: User):
    parts = callback.data.split(":")
    hid = int(parts[1])
    mask = int(parts[2])
    repo = HabitRepository(session)
    await repo.update(hid, schedule_mask=mask)
    sn = SCHEDULE_NAMES.get(mask, "Пользовательский")
    await callback.answer(f"📅 {sn}")
    h = await repo.get_by_id(hid)
    text = (
        f"{h.emoji} *{h.name}*\n\n"
        f"🔥 {h.current_streak}d | 🏆 {h.best_streak}d\n"
        f"📅 График: *{sn}*"
    )
    try:
        await callback.message.edit_text(text, reply_markup=habit_schedule_keyboard(hid))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("habit:del:"))
async def cb_del(callback: CallbackQuery):
    hid = int(callback.data.split(":")[2])
    try:
        await callback.message.edit_text("🗑 *Удалить?*", reply_markup=habit_delete_confirm_keyboard(hid))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("habit:del_yes:"))
async def cb_del_yes(callback: CallbackQuery, session: AsyncSession, db_user: User):
    hid = int(callback.data.split(":")[2])
    repo = HabitRepository(session)
    h = await repo.get_by_id(hid)
    if not h or h.user_id != db_user.id:
        await callback.answer("Нет")
        return
    await repo.update(hid, is_active=False)
    try:
        await callback.message.edit_text(f"🗑 *{h.name}*", reply_markup=habits_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer("Удалено")


@router.message(F.text == "🔄 Привычки")
async def reply(message: Message, session: AsyncSession, db_user: User):
    svc = HabitService(session)
    h = await svc.get_user_habits(db_user.id)
    if h:
        await message.answer("🔄 *Отметь:*", reply_markup=habits_check_keyboard(h))
    else:
        await message.answer("🔄 *Привычки*", reply_markup=habits_menu_keyboard())
