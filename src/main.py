import asyncio
import logging

from src.config import settings
from src.bot.loader import bot, dp, setup_routers
from src.bot.middlewares.db_session import DbSessionMiddleware
from src.bot.middlewares.auth import AuthMiddleware
from src.bot.middlewares.throttling import ThrottlingMiddleware

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

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot is running in polling mode")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())