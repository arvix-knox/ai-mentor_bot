from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Задачи"),
                KeyboardButton(text="🔄 Привычки"),
            ],
            [
                KeyboardButton(text="📝 Журнал"),
                KeyboardButton(text="🤖 AI"),
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="📈 Обзор недели"),
            ],
        ],
        resize_keyboard=True,
    )
