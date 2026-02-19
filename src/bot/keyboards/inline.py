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
            InlineKeyboardButton(text="📈 Обзор недели", callback_data="menu:review"),
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ],
    ])


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новая задача", callback_data="task:add")],
        [
            InlineKeyboardButton(text="📋 Все", callback_data="task:list:all"),
            InlineKeyboardButton(text="⬜ Активные", callback_data="task:list:active"),
        ],
        [
            InlineKeyboardButton(text="✅ Готовые", callback_data="task:list:done"),
            InlineKeyboardButton(text="🔴 Просроченные", callback_data="task:list:overdue"),
        ],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
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
            InlineKeyboardButton(text="⏰ Напоминание", callback_data=f"task:remind:{task_id}"),
        ])
        buttons.append([
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task:del:{task_id}"),
        ])
    elif status == "done":
        buttons.append([
            InlineKeyboardButton(text="↩️ Вернуть", callback_data=f"task:reopen:{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task:del:{task_id}"),
        ])
    buttons.append([InlineKeyboardButton(text="◀️ К задачам", callback_data="task:list:all")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def task_list_with_items(tasks: list) -> InlineKeyboardMarkup:
    buttons = []
    for t in tasks[:10]:
        si = {"todo": "⬜", "in_progress": "🔄", "done": "✅"}.get(t.status, "⬜")
        pi = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(t.priority, "🟡")
        buttons.append([InlineKeyboardButton(text=f"{si}{pi} {t.title[:30]}", callback_data=f"task:view:{t.id}")])
    buttons.append([
        InlineKeyboardButton(text="➕ Новая", callback_data="task:add"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def task_priority_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Low", callback_data="tpriority:low"),
            InlineKeyboardButton(text="🟡 Medium", callback_data="tpriority:medium"),
        ],
        [
            InlineKeyboardButton(text="🟠 High", callback_data="tpriority:high"),
            InlineKeyboardButton(text="🔴 Critical", callback_data="tpriority:critical"),
        ],
    ])


def task_deadline_keyboard() -> InlineKeyboardMarkup:
    from datetime import date, timedelta
    today = date.today()
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Сегодня", callback_data=f"tdeadline:{today}"),
            InlineKeyboardButton(text="📅 Завтра", callback_data=f"tdeadline:{today + timedelta(1)}"),
        ],
        [
            InlineKeyboardButton(text="📅 Через 3 дня", callback_data=f"tdeadline:{today + timedelta(3)}"),
            InlineKeyboardButton(text="📅 Через неделю", callback_data=f"tdeadline:{today + timedelta(7)}"),
        ],
        [
            InlineKeyboardButton(text="📅 Через 2 недели", callback_data=f"tdeadline:{today + timedelta(14)}"),
            InlineKeyboardButton(text="📅 Через месяц", callback_data=f"tdeadline:{today + timedelta(30)}"),
        ],
        [InlineKeyboardButton(text="⏭ Без дедлайна", callback_data="tdeadline:none")],
    ])


def remind_time_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌅 Утро", callback_data=f"tremind_period:{task_id}:morning")],
        [InlineKeyboardButton(text="☀️ День", callback_data=f"tremind_period:{task_id}:afternoon")],
        [InlineKeyboardButton(text="🌙 Вечер", callback_data=f"tremind_period:{task_id}:evening")],
        [InlineKeyboardButton(text="🚫 Без напоминания", callback_data=f"task:view:{task_id}")],
    ])


def remind_exact_time_keyboard(task_id: int, period: str) -> InlineKeyboardMarkup:
    times = {
        "morning": [("7:00", "07:00"), ("7:30", "07:30"), ("8:00", "08:00"), ("8:30", "08:30"), ("9:00", "09:00"), ("9:30", "09:30"), ("10:00", "10:00")],
        "afternoon": [("12:00", "12:00"), ("12:30", "12:30"), ("13:00", "13:00"), ("13:30", "13:30"), ("14:00", "14:00"), ("14:30", "14:30"), ("15:00", "15:00")],
        "evening": [("18:00", "18:00"), ("18:30", "18:30"), ("19:00", "19:00"), ("19:30", "19:30"), ("20:00", "20:00"), ("20:30", "20:30"), ("21:00", "21:00")],
    }
    buttons = []
    row = []
    for label, value in times.get(period, []):
        row.append(InlineKeyboardButton(text=label, callback_data=f"tremind_set:{task_id}:{value}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"task:remind:{task_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def habits_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новая привычка", callback_data="habit:add")],
        [
            InlineKeyboardButton(text="✅ Отметить", callback_data="habit:list"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="habit:stats"),
        ],
        [InlineKeyboardButton(text="🗑 Управление", callback_data="habit:manage")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def habits_check_keyboard(habits: list) -> InlineKeyboardMarkup:
    buttons = []
    for h in habits:
        streak = f"🔥{h.current_streak}" if h.current_streak > 0 else "💤0"
        buttons.append([InlineKeyboardButton(text=f"{h.emoji} {h.name} ({streak}d)", callback_data=f"habit:check:{h.id}")])
    buttons.append([
        InlineKeyboardButton(text="◀️ Привычки", callback_data="menu:habits"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def habit_manage_keyboard(habits: list) -> InlineKeyboardMarkup:
    buttons = []
    for h in habits:
        buttons.append([
            InlineKeyboardButton(text=f"{h.emoji} {h.name}", callback_data=f"habit:info:{h.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"habit:del:{h.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Привычки", callback_data="menu:habits")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def habit_delete_confirm_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"habit:del_yes:{habit_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="habit:manage"),
        ],
    ])


def habit_schedule_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Каждый день", callback_data=f"hsched:{habit_id}:127")],
        [InlineKeyboardButton(text="🏢 Будни (Пн-Пт)", callback_data=f"hsched:{habit_id}:31")],
        [InlineKeyboardButton(text="🎉 Выходные (Сб-Вс)", callback_data=f"hsched:{habit_id}:96")],
        [InlineKeyboardButton(text="📆 Через день", callback_data=f"hsched:{habit_id}:85")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"habit:info:{habit_id}")],
    ])


def journal_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Новая запись", callback_data="journal:add")],
        [
            InlineKeyboardButton(text="📄 Последние", callback_data="journal:list"),
            InlineKeyboardButton(text="🔍 Поиск", callback_data="journal:search"),
        ],
        [InlineKeyboardButton(text="🏷 По тегам", callback_data="journal:bytag")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def journal_entry_keyboard(entry_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Связанные", callback_data=f"journal:related:{entry_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"journal:del:{entry_id}"),
        ],
        [
            InlineKeyboardButton(text="📄 Все записи", callback_data="journal:list"),
            InlineKeyboardButton(text="◀️ Журнал", callback_data="menu:journal"),
        ],
    ])


def journal_list_keyboard(entries: list) -> InlineKeyboardMarkup:
    buttons = []
    for e in entries[:8]:
        d = e.created_at.strftime("%d.%m")
        buttons.append([InlineKeyboardButton(text=f"📄 {d} | {e.title[:28]}", callback_data=f"journal:view:{e.id}")])
    buttons.append([
        InlineKeyboardButton(text="✏️ Новая", callback_data="journal:add"),
        InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ai_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    modes = [("🔴 Strict", "strict"), ("🟢 Soft", "soft"), ("🟡 Adaptive", "adaptive")]
    buttons = []
    for text, mode in modes:
        if mode == current_mode:
            text = f"▸ {text} ◂"
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"mode:{mode}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="◀️ Настройки", callback_data="menu:settings")],
    ])


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Режим AI", callback_data="settings:ai_mode")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:notifications")],
        [InlineKeyboardButton(text="🕐 Часовой пояс", callback_data="settings:timezone")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Имя", callback_data="profile:edit:name")],
        [InlineKeyboardButton(text="💻 Стек технологий", callback_data="profile:edit:stack")],
        [InlineKeyboardButton(text="🎯 Цели", callback_data="profile:edit:goals")],
        [InlineKeyboardButton(text="📚 Уровень знаний", callback_data="profile:edit:level_desc")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def stack_select_keyboard() -> InlineKeyboardMarkup:
    stacks = [
        ("🐍 Python", "Python"), ("🌐 JavaScript", "JavaScript"), ("⚛️ React", "React"),
        ("🟢 Node.js", "Node.js"), ("🦀 Rust", "Rust"), ("☕ Java", "Java"),
        ("🔷 TypeScript", "TypeScript"), ("🐹 Go", "Go"), ("💎 C#", "C#"),
        ("🐘 PHP", "PHP"), ("📱 Flutter", "Flutter"), ("🍎 Swift", "Swift"),
        ("🤖 ML/AI", "ML/AI"), ("🗄 SQL", "SQL"), ("🐧 Linux", "Linux"),
        ("🐳 Docker", "Docker"), ("☁️ AWS", "AWS"), ("🔥 FastAPI", "FastAPI"),
    ]
    buttons = []
    row = []
    for label, value in stacks:
        row.append(InlineKeyboardButton(text=label, callback_data=f"stack:toggle:{value}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="stack:done")])
    buttons.append([InlineKeyboardButton(text="◀️ Профиль", callback_data="menu:profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def goals_select_keyboard() -> InlineKeyboardMarkup:
    goals = [
        ("🏢 Устроиться на работу", "get_job"), ("📈 Повышение", "promotion"),
        ("🚀 Свой проект", "own_project"), ("📚 Изучить новый язык", "new_language"),
        ("🧠 Алгоритмы", "algorithms"), ("🌐 Fullstack", "fullstack"),
        ("📱 Мобильная разработка", "mobile"), ("🤖 Machine Learning", "ml"),
        ("🔒 Безопасность", "security"), ("☁️ DevOps", "devops"),
        ("💰 Фриланс", "freelance"), ("🎓 Пройти курс", "course"),
    ]
    buttons = []
    row = []
    for label, value in goals:
        row.append(InlineKeyboardButton(text=label, callback_data=f"goal:toggle:{value}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="goal:done")])
    buttons.append([InlineKeyboardButton(text="◀️ Профиль", callback_data="menu:profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def knowledge_level_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Новичок (0-6 мес)", callback_data="klevel:beginner")],
        [InlineKeyboardButton(text="📗 Junior (6-18 мес)", callback_data="klevel:junior")],
        [InlineKeyboardButton(text="📘 Middle (1.5-4 года)", callback_data="klevel:middle")],
        [InlineKeyboardButton(text="📕 Senior (4+ лет)", callback_data="klevel:senior")],
        [InlineKeyboardButton(text="◀️ Профиль", callback_data="menu:profile")],
    ])


def notification_settings_keyboard(settings_dict: dict) -> InlineKeyboardMarkup:
    def icon(key):
        return "✅" if settings_dict.get(key, True) else "❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{icon('morning')} 🌅 Утренний план", callback_data="notif:toggle:morning")],
        [InlineKeyboardButton(text=f"{icon('evening')} 🌙 Вечернее напоминание", callback_data="notif:toggle:evening")],
        [InlineKeyboardButton(text=f"{icon('motivation')} 💪 Мотивация", callback_data="notif:toggle:motivation")],
        [InlineKeyboardButton(text=f"{icon('streak')} 🔥 Streak alert", callback_data="notif:toggle:streak")],
        [InlineKeyboardButton(text=f"{icon('weekly')} 📊 Недельный обзор", callback_data="notif:toggle:weekly")],
        [InlineKeyboardButton(text="🕐 Время уведомлений", callback_data="notif:time")],
        [InlineKeyboardButton(text="◀️ Настройки", callback_data="menu:settings")],
    ])


def notif_time_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌅 Утреннее время", callback_data="notif_time:morning")],
        [InlineKeyboardButton(text="🌙 Вечернее время", callback_data="notif_time:evening")],
        [InlineKeyboardButton(text="◀️ Уведомления", callback_data="settings:notifications")],
    ])


def notif_exact_time_keyboard(period: str) -> InlineKeyboardMarkup:
    times = {
        "morning": [("7:00","07:00"),("7:30","07:30"),("8:00","08:00"),("8:30","08:30"),("9:00","09:00"),("9:30","09:30"),("10:00","10:00")],
        "evening": [("19:00","19:00"),("19:30","19:30"),("20:00","20:00"),("20:30","20:30"),("21:00","21:00"),("21:30","21:30"),("22:00","22:00")],
    }
    buttons = []
    row = []
    for label, value in times.get(period, []):
        row.append(InlineKeyboardButton(text=label, callback_data=f"notif_set:{period}:{value}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notif:time")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def timezone_keyboard() -> InlineKeyboardMarkup:
    zones = [
        ("🇷🇺 Москва (UTC+3)", "Europe/Moscow"),
        ("🇷🇺 Екатеринбург (UTC+5)", "Asia/Yekaterinburg"),
        ("🇷🇺 Новосибирск (UTC+7)", "Asia/Novosibirsk"),
        ("🇷🇺 Владивосток (UTC+10)", "Asia/Vladivostok"),
        ("🇰🇿 Алматы (UTC+6)", "Asia/Almaty"),
        ("🇺🇦 Киев (UTC+2)", "Europe/Kiev"),
        ("🇺🇿 Ташкент (UTC+5)", "Asia/Tashkent"),
        ("🇬🇧 Лондон (UTC+0)", "Europe/London"),
    ]
    buttons = [[InlineKeyboardButton(text=label, callback_data=f"tz:{value}")] for label, value in zones]
    buttons.append([InlineKeyboardButton(text="◀️ Настройки", callback_data="menu:settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_keyboard(target: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=target)],
    ])


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
            InlineKeyboardButton(text="❌ Нет", callback_data=no_data),
        ],
    ])
