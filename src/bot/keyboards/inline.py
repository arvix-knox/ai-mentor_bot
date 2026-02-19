from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def confirm_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да",
                callback_data=f"{action}_confirm:{item_id}",
            ),
            InlineKeyboardButton(
                text="❌ Нет",
                callback_data=f"{action}_cancel:{item_id}",
            ),
        ]
    ])


def back_keyboard(command: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"back:{command}",
            )
        ]
    ])