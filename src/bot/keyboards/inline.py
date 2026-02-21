from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from src.config import settings


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
            InlineKeyboardButton(text="🎵 Плейлисты", callback_data="menu:playlists"),
            InlineKeyboardButton(text="🎓 Обучение", callback_data="menu:learning"),
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
        ],
    ])


def webapp_open_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Открыть Web App", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
        [InlineKeyboardButton(text="🔗 Открыть в браузере", url=settings.WEBAPP_URL)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")],
    ])


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Новая задача", callback_data="task:add"),
            InlineKeyboardButton(text="⚡ Полезная задача", callback_data="task:quick:add"),
        ],
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
        [InlineKeyboardButton(text="🗓 Конкретная дата (YYYY-MM-DD)", callback_data="tdeadline:custom")],
    ])


def remind_time_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Вкл напоминание", callback_data=f"tremind_on:{task_id}")],
        [InlineKeyboardButton(text="🌅 Утро", callback_data=f"tremind_period:{task_id}:morning")],
        [InlineKeyboardButton(text="☀️ День", callback_data=f"tremind_period:{task_id}:afternoon")],
        [InlineKeyboardButton(text="🌙 Вечер", callback_data=f"tremind_period:{task_id}:evening")],
        [InlineKeyboardButton(text="🕐 Другое время (HH:MM)", callback_data=f"tremind_custom:{task_id}")],
        [InlineKeyboardButton(text="🚫 Выкл напоминание", callback_data=f"tremind_off:{task_id}")],
        [InlineKeyboardButton(text="◀️ К задаче", callback_data=f"task:view:{task_id}")],
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
    buttons.append([InlineKeyboardButton(text="🕐 Другое (HH:MM)", callback_data=f"tremind_custom:{task_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"task:remind:{task_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def task_recurrence_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Каждый день", callback_data="trecur:daily")],
        [InlineKeyboardButton(text="🗓 Каждую неделю", callback_data="trecur:weekly")],
        [InlineKeyboardButton(text="🗓 Каждый месяц", callback_data="trecur:monthly")],
        [InlineKeyboardButton(text="🎯 Конкретная дата", callback_data="trecur:on_date")],
        [InlineKeyboardButton(text="⏭ Без повторений", callback_data="trecur:none")],
    ])


def task_quick_difficulty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Легко", callback_data="tquick:diff:low"),
            InlineKeyboardButton(text="🟡 Средне", callback_data="tquick:diff:medium"),
        ],
        [
            InlineKeyboardButton(text="🟠 Сложно", callback_data="tquick:diff:high"),
            InlineKeyboardButton(text="🔴 Очень сложно", callback_data="tquick:diff:critical"),
        ],
        [InlineKeyboardButton(text="◀️ К задачам", callback_data="menu:tasks")],
    ])


def reminder_toggle_keyboard(entity: str, entity_id: int) -> InlineKeyboardMarkup:
    prefix = "t" if entity == "task" else "h"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Вкл", callback_data=f"{prefix}remind_enable:{entity_id}")],
        [InlineKeyboardButton(text="🚫 Выкл", callback_data=f"{prefix}remind_disable:{entity_id}")],
        [InlineKeyboardButton(text="🕐 Выбрать время", callback_data=f"{prefix}remind_custom:{entity_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ])


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
            InlineKeyboardButton(text="🧠 Проверить AI", callback_data=f"journal:ai_check:{entry_id}"),
        ],
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
        [InlineKeyboardButton(text="🧠 Права AI", callback_data="settings:ai_permissions")],
        [InlineKeyboardButton(text="🧾 AI-ежедневка", callback_data="settings:ai_daily_brief")],
        [InlineKeyboardButton(text="📔 AI-проверка журнала", callback_data="settings:ai_journal_review")],
        [InlineKeyboardButton(text="✍️ Текст напоминаний", callback_data="settings:remind_template")],
        [InlineKeyboardButton(text="🗑 Очистка данных", callback_data="settings:data_cleanup")],
        [InlineKeyboardButton(text="🕐 Часовой пояс", callback_data="settings:timezone")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Имя", callback_data="profile:edit:name")],
        [InlineKeyboardButton(text="💻 Стек технологий", callback_data="profile:edit:stack")],
        [InlineKeyboardButton(text="🎯 Цели", callback_data="profile:edit:goals")],
        [InlineKeyboardButton(text="📚 Уровень знаний", callback_data="profile:edit:level_desc")],
        [InlineKeyboardButton(text="🏆 Достижения", callback_data="profile:achievements")],
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
        ("⚙️ Django", "Django"), ("📡 gRPC", "gRPC"), ("🧱 PostgreSQL", "PostgreSQL"),
        ("📦 Redis", "Redis"), ("☸️ Kubernetes", "Kubernetes"), ("🧪 Pytest", "Pytest"),
        ("🧬 GraphQL", "GraphQL"), ("🌩 GCP", "GCP"), ("🧭 Terraform", "Terraform"),
        ("🔐 CyberSecurity", "CyberSecurity"), ("📊 Data Engineering", "Data Engineering"),
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
        [InlineKeyboardButton(text=f"{icon('task_remind_default')} 📋 Напоминания задач", callback_data="notif:toggle:task_remind_default")],
        [InlineKeyboardButton(text=f"{icon('habit_remind_default')} 🔄 Напоминания привычек", callback_data="notif:toggle:habit_remind_default")],
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
    buttons.append([InlineKeyboardButton(text="🕐 Другое (HH:MM)", callback_data=f"notif_set:{period}:custom")])
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


def ai_permissions_keyboard(perms: dict) -> InlineKeyboardMarkup:
    def icon(key: str) -> str:
        return "🟢" if perms.get(key, True) else "⚪"

    buttons = [
        [InlineKeyboardButton(text=f"{icon('read_tasks')} Читать задачи", callback_data="ai_perm:toggle:read_tasks")],
        [InlineKeyboardButton(text=f"{icon('read_habits')} Читать привычки", callback_data="ai_perm:toggle:read_habits")],
        [InlineKeyboardButton(text=f"{icon('read_journal')} Читать журнал", callback_data="ai_perm:toggle:read_journal")],
        [InlineKeyboardButton(text=f"{icon('read_stats')} Читать статистику", callback_data="ai_perm:toggle:read_stats")],
        [InlineKeyboardButton(text=f"{icon('create_tasks')} Создавать задачи", callback_data="ai_perm:toggle:create_tasks")],
        [InlineKeyboardButton(text=f"{icon('modify_tasks')} Изменять задачи", callback_data="ai_perm:toggle:modify_tasks")],
        [InlineKeyboardButton(text=f"{icon('read_resources')} Читать обучение", callback_data="ai_perm:toggle:read_resources")],
        [InlineKeyboardButton(text="◀️ Настройки", callback_data="menu:settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def data_cleanup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить профиль", callback_data="cleanup:profile")],
        [InlineKeyboardButton(text="🧠 Удалить AI историю", callback_data="cleanup:history")],
        [InlineKeyboardButton(text="◀️ Настройки", callback_data="menu:settings")],
    ])


def history_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕐 За день", callback_data="cleanup:history:day")],
        [InlineKeyboardButton(text="📆 За неделю", callback_data="cleanup:history:week")],
        [InlineKeyboardButton(text="🗓 За месяц", callback_data="cleanup:history:month")],
        [InlineKeyboardButton(text="🧾 За год", callback_data="cleanup:history:year")],
        [InlineKeyboardButton(text="💥 Полностью", callback_data="cleanup:history:all")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings:data_cleanup")],
    ])


def learning_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ресурс", callback_data="learn:add")],
        [InlineKeyboardButton(text="🧠 Подобрать по теме", callback_data="learn:suggest")],
        [InlineKeyboardButton(text="📚 Мои ресурсы", callback_data="learn:list")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def learning_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Статья", callback_data="learn:type:article")],
        [InlineKeyboardButton(text="🎬 Видео", callback_data="learn:type:video")],
        [InlineKeyboardButton(text="🎓 Курс", callback_data="learn:type:course")],
        [InlineKeyboardButton(text="⚡ Краткое объяснение", callback_data="learn:type:summary")],
    ])


def learning_item_keyboard(resource_id: int, completed: bool = False) -> InlineKeyboardMarkup:
    done_text = "✅ Пройдено" if completed else "✔️ Отметить пройденным"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=done_text, callback_data=f"learn:done:{resource_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"learn:del:{resource_id}")],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="learn:list")],
    ])


def learning_list_keyboard(resources: list) -> InlineKeyboardMarkup:
    buttons = []
    for r in resources[:12]:
        icon = "✅" if r.is_completed else "📌"
        buttons.append([InlineKeyboardButton(text=f"{icon} {r.title[:40]}", callback_data=f"learn:view:{r.id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Обучение", callback_data="menu:learning")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def playlists_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новый плейлист", callback_data="plist:add")],
        [InlineKeyboardButton(text="🎵 Мои плейлисты", callback_data="plist:list")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu:main")],
    ])


def playlist_list_keyboard(playlists: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in playlists[:12]:
        buttons.append([InlineKeyboardButton(text=f"{p.emoji} {p.name[:40]}", callback_data=f"plist:view:{p.id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Плейлисты", callback_data="menu:playlists")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def playlist_item_keyboard(playlist_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить трек", callback_data=f"plist:add_track:{playlist_id}")],
        [InlineKeyboardButton(text="▶️ Слушать", callback_data=f"plist:play:{playlist_id}")],
        [InlineKeyboardButton(text="🧹 Выйти и удалить сообщения", callback_data=f"plist:stop:{playlist_id}")],
        [InlineKeyboardButton(text="🗑 Удалить плейлист", callback_data=f"plist:del:{playlist_id}")],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="plist:list")],
    ])
