import asyncio
import logging

from aiogram.exceptions import TelegramNetworkError

from src.config import settings
from src.bot.loader import bot, dp, setup_routers
from src.bot.middlewares.db_session import DbSessionMiddleware
from src.bot.middlewares.auth import AuthMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware
from src.core.scheduler import reminder_scheduler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting bot...")

    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(ThrottlingMiddleware())

    setup_routers()
    reminder_scheduler.start()

    retry_delay = 8
    try:
        while True:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info("Bot is running in polling mode")
                await dp.start_polling(bot)
                break
            except TelegramNetworkError as e:
                logger.error(
                    "Telegram API недоступен (%s). Повтор через %s сек.",
                    e,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
            except Exception as e:
                logger.exception("Критическая ошибка polling: %s", e)
                await asyncio.sleep(retry_delay)
    finally:
        try:
            reminder_scheduler.scheduler.shutdown(wait=False)
        except Exception:
            pass
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
