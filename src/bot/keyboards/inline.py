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
        [
            InlineKeyboardButton(text="📈 Обзор недели", callback_data="menu:review"),
        ],
    ])


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Новая задача", callback_data="task:add"),
        ],
        [
            InlineKeyboardButton(text="📋 Все", callback_data="task:list:all"),
            InlineKeyboardButton(text="⬜ Активные", callback_data="task:list:active"),
            InlineKeyboardButton(text="✅ Готовые", callback_data="task:list:done"),
        ],
        [
            InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
        ],
    ])


def task_item_keyboard(task_id: int, status: str = "todo") -> InlineKeyboardMarkup:
    buttons = []
    if status in ("todo", "in_progress"):
        buttons.append([
            InlineKeyboardButton(text="✅ Выполнить", callback_data=f"task:done:{task_id}"),
            InlineKeyboardButton(text="🔄 В работу", callback_data=f"task:progress:{task_id}"),
        ])
        buttons.append([
            InlineKeyboardButton(text="✏️ Изменить", callback_data=f"task:edit:{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task:del:{task_id}"),
        ])
    elif status == "done":
        buttons.append([
            InlineKeyboardButton(text="↩️ Вернуть", callback_data=f"task:reopen:{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task:del:{task_id}"),
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ К задачам", callback_data="task:list:all"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def task_list_with_items(tasks: list) -> InlineKeyboardMarkup:
    buttons = []
    for t in tasks[:10]:
        status_icon = {"todo": "⬜", "in_progress": "🔄", "done": "✅"}.get(t.status, "⬜")
        priority_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(t.priority, "🟡")
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon}{priority_icon} {t.title[:35]}",
                callback_data=f"task:view:{t.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Новая", callback_data="task:add"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def habits_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Новая привычка", callback_data="habit:add"),
        ],
        [
            InlineKeyboardButton(text="✅ Отметить", callback_data="habit:list"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="habit:stats"),
        ],
        [
            InlineKeyboardButton(text="🗑 Управление", callback_data="habit:manage"),
        ],
        [
            InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
        ],
    ])


def habits_check_keyboard(habits: list) -> InlineKeyboardMarkup:
    buttons = []
    for habit in habits:
        streak = f"🔥{habit.current_streak}" if habit.current_streak > 0 else "💤0"
        buttons.append([
            InlineKeyboardButton(
                text=f"{habit.emoji} {habit.name} ({streak}d)",
                callback_data=f"habit:check:{habit.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Привычки", callback_data="menu:habits"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def habit_manage_keyboard(habits: list) -> InlineKeyboardMarkup:
    buttons = []
    for habit in habits:
        buttons.append([
            InlineKeyboardButton(
                text=f"{habit.emoji} {habit.name}",
                callback_data=f"habit:info:{habit.id}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"habit:del:{habit.id}",
            ),
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Привычки", callback_data="menu:habits"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def habit_delete_confirm_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"habit:del_yes:{habit_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="habit:manage"),
        ],
    ])


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


def journal_entry_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"journal:del:{entry_id}"),
            InlineKeyboardButton(text="📄 Все записи", callback_data="journal:list"),
        ],
        [
            InlineKeyboardButton(text="◀️ Журнал", callback_data="menu:journal"),
        ],
    ])


def journal_list_keyboard(entries: list) -> InlineKeyboardMarkup:
    buttons = []
    for e in entries[:8]:
        date_str = e.created_at.strftime("%d.%m")
        buttons.append([
            InlineKeyboardButton(
                text=f"📄 {date_str} | {e.title[:30]}",
                callback_data=f"journal:view:{e.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="✏️ Новая", callback_data="journal:add"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ai_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    modes = [
        ("🔴 Strict", "strict"),
        ("🟢 Soft", "soft"),
        ("🟡 Adaptive", "adaptive"),
    ]
    buttons = []
    for text, mode in modes:
        if mode == current_mode:
            text = f"▸ {text} ◂"
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"mode:{mode}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def back_keyboard(target: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=target)],
    ])


def confirm_delete_keyboard(action_yes: str, action_no: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=action_yes),
            InlineKeyboardButton(text="❌ Нет", callback_data=action_no),
        ],
    ])
