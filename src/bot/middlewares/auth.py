from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from src.config import settings
from src.repositories.user_repo import UserRepository


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return

        if settings.allowed_ids and user.id not in settings.allowed_ids:
            if isinstance(event, Message):
                await event.answer("⛔ Доступ запрещён.")
            return

        session = data.get("session")
        if session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            data["db_user"] = db_user

        return await handler(event, data)