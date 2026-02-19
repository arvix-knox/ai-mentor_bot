from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Tasks"),
                KeyboardButton(text="🔄 Habits"),
            ],
            [
                KeyboardButton(text="📝 Journal"),
                KeyboardButton(text="🤖 AI"),
            ],
            [
                KeyboardButton(text="📊 Stats"),
                KeyboardButton(text="⚙️ Settings"),
            ],
        ],
        resize_keyboard=True,
    )