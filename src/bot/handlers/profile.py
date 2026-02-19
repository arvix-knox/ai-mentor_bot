import json
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.user_repo import UserRepository
from src.services.gamification_service import GamificationService
from src.services.analytics_service import AnalyticsService
from src.bot.keyboards.inline import (
    profile_keyboard, stack_select_keyboard, goals_select_keyboard,
    knowledge_level_keyboard, settings_keyboard, ai_mode_keyboard,
    notification_settings_keyboard, notif_time_period_keyboard,
    notif_exact_time_keyboard, timezone_keyboard, back_keyboard,
    main_menu_keyboard,
)

router = Router()

KNOWLEDGE_LEVELS = {
    "beginner": "🌱 Новичок",
    "junior": "📗 Junior",
    "middle": "📘 Middle",
    "senior": "📕 Senior",
}

GOAL_LABELS = {
    "get_job": "🏢 Устроиться", "promotion": "📈 Повышение",
    "own_project": "🚀 Свой проект", "new_language": "📚 Новый язык",
    "algorithms": "🧠 Алгоритмы", "fullstack": "🌐 Fullstack",
    "mobile": "📱 Мобильная", "ml": "🤖 ML", "security": "🔒 Безопасность",
    "devops": "☁️ DevOps", "freelance": "💰 Фриланс", "course": "🎓 Курс",
}

DEFAULT_NOTIF = {
    "morning": True, "evening": True, "motivation": True,
    "streak": True, "weekly": True,
    "morning_time": "08:00", "evening_time": "21:00",
}


class ProfileStates(StatesGroup):
    waiting_name = State()
    waiting_custom_stack = State()
    waiting_custom_goal = State()


def _get_user_data(user, field):
    try:
        val = getattr(user, field, None)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return {}


def _get_notif_settings(user):
    data = _get_user_data(user, "goals")
    if isinstance(data, dict) and "notifications" in data:
        return {**DEFAULT_NOTIF, **data["notifications"]}
    return dict(DEFAULT_NOTIF)


def _save_notif_settings(user, notif, user_repo, user_id):
    data = _get_user_data(user, "goals")
    if not isinstance(data, dict):
        data = {}
    data["notifications"] = notif
    return data


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession, db_user: User):
    await _show_profile(message, db_user)


@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await _show_profile(callback.message, db_user, edit=True)
    await callback.answer()


@router.message(F.text == "👤 Профиль")
async def reply_profile(message: Message, session: AsyncSession, db_user: User):
    await _show_profile(message, db_user)


async def _show_profile(msg, user, edit=False):
    stack = []
    goals_data = {}
    try:
        if user.tech_stack:
            stack = json.loads(user.tech_stack)
        if user.goals:
            goals_data = json.loads(user.goals)
    except Exception:
        pass
    stack_text = ", ".join(stack) if stack else "❌ не указан"
    goals_list = goals_data.get("goals", [])
    goals_text = ", ".join(GOAL_LABELS.get(g, g) for g in goals_list) if goals_list else "❌ не указаны"
    klevel = goals_data.get("knowledge_level", "")
    klevel_text = KNOWLEDGE_LEVELS.get(klevel, "❌ не указан")
    level_info = GamificationService.format_level_progress(user.total_xp_earned)
    text = (
        f"👤 *Профиль*\n\n"
        f"📛 Имя: *{user.first_name}*\n"
        f"💻 Стек: {stack_text}\n"
        f"🎯 Цели: {goals_text}\n"
        f"📚 Уровень: {klevel_text}\n\n"
        f"{level_info}\n\n"
        f"Нажми чтобы изменить ⬇️"
    )
    kb = profile_keyboard()
    if edit:
        try:
            await msg.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            pass
    else:
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data == "profile:edit:name")
async def cb_edit_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_name)
    await callback.message.edit_text("📛 Отправь новое имя:")
    await callback.answer()


@router.message(ProfileStates.waiting_name)
async def name_input(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    name = message.text.strip()[:50]
    repo = UserRepository(session)
    await repo.update(db_user.id, first_name=name)
    db_user.first_name = name
    await message.answer(f"✅ Имя: *{name}*")
    await _show_profile(message, db_user)
    await state.clear()


@router.callback_query(F.data == "profile:edit:stack")
async def cb_edit_stack(callback: CallbackQuery, session: AsyncSession, db_user: User):
    stack = []
    try:
        if db_user.tech_stack:
            stack = json.loads(db_user.tech_stack)
    except Exception:
        pass
    stack_text = ", ".join(stack) if stack else "пусто"
    await callback.message.edit_text(
        f"💻 *Стек технологий*\n\nТекущий: {stack_text}\n\nВыбери технологии:",
        reply_markup=stack_select_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stack:toggle:"))
async def cb_stack_toggle(callback: CallbackQuery, session: AsyncSession, db_user: User):
    tech = callback.data.split(":")[2]
    stack = []
    try:
        if db_user.tech_stack:
            stack = json.loads(db_user.tech_stack)
    except Exception:
        pass
    if tech in stack:
        stack.remove(tech)
        await callback.answer(f"❌ {tech} убран")
    else:
        stack.append(tech)
        await callback.answer(f"✅ {tech} добавлен")
    repo = UserRepository(session)
    await repo.update(db_user.id, tech_stack=json.dumps(stack))
    db_user.tech_stack = json.dumps(stack)
    stack_text = ", ".join(stack) if stack else "пусто"
    try:
        await callback.message.edit_text(
            f"💻 *Стек технологий*\n\nТекущий: *{stack_text}*\n\nВыбери технологии:",
            reply_markup=stack_select_keyboard(),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "stack:done")
async def cb_stack_done(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await _show_profile(callback.message, db_user, edit=True)
    await callback.answer("Сохранено!")


@router.callback_query(F.data == "profile:edit:goals")
async def cb_edit_goals(callback: CallbackQuery, session: AsyncSession, db_user: User):
    goals_data = _get_user_data(db_user, "goals")
    goals_list = goals_data.get("goals", []) if isinstance(goals_data, dict) else []
    current = ", ".join(GOAL_LABELS.get(g, g) for g in goals_list) if goals_list else "пусто"
    await callback.message.edit_text(
        f"🎯 *Цели*\n\nТекущие: {current}\n\nВыбери:",
        reply_markup=goals_select_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("goal:toggle:"))
async def cb_goal_toggle(callback: CallbackQuery, session: AsyncSession, db_user: User):
    goal = callback.data.split(":")[2]
    goals_data = _get_user_data(db_user, "goals")
    if not isinstance(goals_data, dict):
        goals_data = {}
    goals_list = goals_data.get("goals", [])
    if goal in goals_list:
        goals_list.remove(goal)
        await callback.answer(f"❌ Убрано")
    else:
        goals_list.append(goal)
        await callback.answer(f"✅ Добавлено")
    goals_data["goals"] = goals_list
    repo = UserRepository(session)
    await repo.update(db_user.id, goals=json.dumps(goals_data))
    db_user.goals = json.dumps(goals_data)
    current = ", ".join(GOAL_LABELS.get(g, g) for g in goals_list) if goals_list else "пусто"
    try:
        await callback.message.edit_text(
            f"🎯 *Цели*\n\nТекущие: *{current}*\n\nВыбери:",
            reply_markup=goals_select_keyboard(),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "goal:done")
async def cb_goal_done(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await _show_profile(callback.message, db_user, edit=True)
    await callback.answer("Сохранено!")


@router.callback_query(F.data == "profile:edit:level_desc")
async def cb_edit_level(callback: CallbackQuery):
    await callback.message.edit_text("📚 *Уровень знаний*\n\nВыбери:", reply_markup=knowledge_level_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("klevel:"))
async def cb_klevel(callback: CallbackQuery, session: AsyncSession, db_user: User):
    level = callback.data.split(":")[1]
    goals_data = _get_user_data(db_user, "goals")
    if not isinstance(goals_data, dict):
        goals_data = {}
    goals_data["knowledge_level"] = level
    repo = UserRepository(session)
    await repo.update(db_user.id, goals=json.dumps(goals_data))
    db_user.goals = json.dumps(goals_data)
    await callback.answer(f"✅ {KNOWLEDGE_LEVELS.get(level, level)}")
    await _show_profile(callback.message, db_user, edit=True)


@router.message(Command("settings"))
async def cmd_settings(message: Message, **kwargs):
    await message.answer("⚙️ *Настройки*", reply_markup=settings_keyboard())


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery):
    try:
        await callback.message.edit_text("⚙️ *Настройки*", reply_markup=settings_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "settings:ai_mode")
async def cb_ai_mode(callback: CallbackQuery, session: AsyncSession, db_user: User):
    MODE_DESC = {
        "strict": "🔴 *Strict* — жёсткий",
        "soft": "🟢 *Soft* — мягкий",
        "adaptive": "🟡 *Adaptive* — адаптивный",
    }
    try:
        await callback.message.edit_text(
            f"🤖 *Режим AI*\n\nТекущий: {MODE_DESC.get(db_user.ai_mode, db_user.ai_mode)}",
            reply_markup=ai_mode_keyboard(db_user.ai_mode),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode_set(callback: CallbackQuery, session: AsyncSession, db_user: User):
    mode = callback.data.split(":")[1]
    if mode not in ("strict", "soft", "adaptive"):
        await callback.answer("Ошибка")
        return
    repo = UserRepository(session)
    await repo.update(db_user.id, ai_mode=mode)
    db_user.ai_mode = mode
    MODE_DESC = {"strict": "🔴 Strict", "soft": "🟢 Soft", "adaptive": "🟡 Adaptive"}
    try:
        await callback.message.edit_text(
            f"✅ Режим: *{MODE_DESC[mode]}*",
            reply_markup=ai_mode_keyboard(mode),
        )
    except TelegramBadRequest:
        pass
    await callback.answer("Сохранено!")


@router.callback_query(F.data == "settings:notifications")
async def cb_notifications(callback: CallbackQuery, session: AsyncSession, db_user: User):
    notif = _get_notif_settings(db_user)
    try:
        await callback.message.edit_text(
            f"🔔 *Уведомления*\n\n"
            f"🌅 Утро: {notif.get('morning_time', '08:00')}\n"
            f"🌙 Вечер: {notif.get('evening_time', '21:00')}",
            reply_markup=notification_settings_keyboard(notif),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("notif:toggle:"))
async def cb_notif_toggle(callback: CallbackQuery, session: AsyncSession, db_user: User):
    key = callback.data.split(":")[2]
    notif = _get_notif_settings(db_user)
    notif[key] = not notif.get(key, True)
    goals_data = _get_user_data(db_user, "goals")
    if not isinstance(goals_data, dict):
        goals_data = {}
    goals_data["notifications"] = notif
    repo = UserRepository(session)
    await repo.update(db_user.id, goals=json.dumps(goals_data))
    db_user.goals = json.dumps(goals_data)
    status = "✅ Вкл" if notif[key] else "❌ Выкл"
    await callback.answer(f"{key}: {status}")
    try:
        await callback.message.edit_text(
            f"🔔 *Уведомления*\n\n"
            f"🌅 Утро: {notif.get('morning_time', '08:00')}\n"
            f"🌙 Вечер: {notif.get('evening_time', '21:00')}",
            reply_markup=notification_settings_keyboard(notif),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "notif:time")
async def cb_notif_time(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🕐 *Время уведомлений*\n\nВыбери:", reply_markup=notif_time_period_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("notif_time:"))
async def cb_notif_time_period(callback: CallbackQuery):
    period = callback.data.split(":")[1]
    label = "🌅 Утро" if period == "morning" else "🌙 Вечер"
    try:
        await callback.message.edit_text(f"{label} — выбери время:", reply_markup=notif_exact_time_keyboard(period))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("notif_set:"))
async def cb_notif_set_time(callback: CallbackQuery, session: AsyncSession, db_user: User):
    parts = callback.data.split(":")
    period = parts[1]
    time_val = parts[2]
    notif = _get_notif_settings(db_user)
    notif[f"{period}_time"] = time_val
    goals_data = _get_user_data(db_user, "goals")
    if not isinstance(goals_data, dict):
        goals_data = {}
    goals_data["notifications"] = notif
    repo = UserRepository(session)
    await repo.update(db_user.id, goals=json.dumps(goals_data))
    db_user.goals = json.dumps(goals_data)
    await callback.answer(f"✅ {period}: {time_val}")
    try:
        await callback.message.edit_text(
            f"🔔 *Уведомления*\n\n"
            f"🌅 Утро: {notif.get('morning_time', '08:00')}\n"
            f"🌙 Вечер: {notif.get('evening_time', '21:00')}",
            reply_markup=notification_settings_keyboard(notif),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "settings:timezone")
async def cb_timezone(callback: CallbackQuery, session: AsyncSession, db_user: User):
    try:
        await callback.message.edit_text(
            f"🕐 *Часовой пояс*\n\nТекущий: *{db_user.timezone}*\n\nВыбери:",
            reply_markup=timezone_keyboard(),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("tz:"))
async def cb_tz_set(callback: CallbackQuery, session: AsyncSession, db_user: User):
    tz = callback.data.split(":", 1)[1]
    repo = UserRepository(session)
    await repo.update(db_user.id, timezone=tz)
    db_user.timezone = tz
    await callback.answer(f"✅ {tz}")
    try:
        await callback.message.edit_text(f"✅ Часовой пояс: *{tz}*", reply_markup=settings_keyboard())
    except TelegramBadRequest:
        pass


@router.message(Command("mode"))
async def cmd_mode(message: Message, session: AsyncSession, db_user: User):
    await message.answer(
        f"🤖 *Режим AI*: *{db_user.ai_mode}*",
        reply_markup=ai_mode_keyboard(db_user.ai_mode),
    )


@router.message(Command("review"))
async def cmd_review(message: Message, session: AsyncSession, db_user: User):
    msg = await message.answer("📊 Генерирую...")
    analytics_svc = AnalyticsService(session)
    data = await analytics_svc.generate_weekly_report(db_user.id)
    report = AnalyticsService.format_weekly_report(data)
    try:
        await msg.edit_text(report, reply_markup=back_keyboard("menu:main"))
    except TelegramBadRequest:
        await msg.edit_text("📊 Готово", reply_markup=back_keyboard("menu:main"))


@router.callback_query(F.data == "menu:review")
async def cb_review(callback: CallbackQuery, session: AsyncSession, db_user: User):
    await callback.answer("Генерирую...")
    try:
        await callback.message.edit_text("📊 Генерирую...")
    except TelegramBadRequest:
        pass
    analytics_svc = AnalyticsService(session)
    data = await analytics_svc.generate_weekly_report(db_user.id)
    report = AnalyticsService.format_weekly_report(data)
    try:
        await callback.message.edit_text(report, reply_markup=back_keyboard("menu:main"))
    except TelegramBadRequest:
        pass


@router.message(F.text == "📈 Обзор")
async def reply_review(message: Message, session: AsyncSession, db_user: User):
    await cmd_review(message, session=session, db_user=db_user)
