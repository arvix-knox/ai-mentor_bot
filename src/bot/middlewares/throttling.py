from typing import Callable, Awaitable, Any
from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.user_timestamps: dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        if not user:
            return

        now = datetime.utcnow()
        last_time = self.user_timestamps.get(user.id)

        if last_time and (now - last_time) < timedelta(seconds=self.rate_limit):
            return

        self.user_timestamps[user.id] = now
        return await handler(event, data)