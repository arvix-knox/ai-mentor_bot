from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Задачи", callback_data="menu:tasks"),
            InlineKeyboardButton(text="🔄 Привычки", callback_data="menu:habits"),
        ],
        [
            InlineKeyboardButton(text="📝 Журнал", callback_data="menu:journal"),
            InlineKeyboardButton(text="🤖 AI Наставник", callback_data="menu:ai"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="menu:stats"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ],
    ])


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Новая задача", callback_data="task:add"),
        ],
        [
            InlineKeyboardButton(text="📋 Все задачи", callback_data="task:list:all"),
            InlineKeyboardButton(text="⬜ Активные", callback_data="task:list:active"),
        ],
        [
            InlineKeyboardButton(text="✅ Выполненные", callback_data="task:list:done"),
        ],
        [
            InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
        ],
    ])


def task_item_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выполнить", callback_data=f"task:done:{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task:del:{task_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️ К задачам", callback_data="menu:tasks"),
        ],
    ])


def habits_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Новая привычка", callback_data="habit:add"),
        ],
        [
            InlineKeyboardButton(text="📋 Мои привычки", callback_data="habit:list"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="habit:stats"),
        ],
        [
            InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
        ],
    ])


def habits_check_keyboard(habits: list) -> InlineKeyboardMarkup:
    buttons = []
    for habit in habits:
        streak = f"🔥{habit.current_streak}" if habit.current_streak > 0 else "0"
        buttons.append([
            InlineKeyboardButton(
                text=f"{habit.emoji} {habit.name} ({streak}d)",
                callback_data=f"habit:check:{habit.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def journal_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Новая запись", callback_data="journal:add"),
        ],
        [
            InlineKeyboardButton(text="📄 Последние", callback_data="journal:list"),
            InlineKeyboardButton(text="🔍 Поиск", callback_data="journal:search"),
        ],
        [
            InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
        ],
    ])


def ai_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    modes = [
        ("🔴 Strict", "strict"),
        ("🟢 Soft", "soft"),
        ("🟡 Adaptive", "adaptive"),
    ]
    buttons = []
    for text, mode in modes:
        if mode == current_mode:
            text = f"✓ {text}"
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"mode:{mode}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])
