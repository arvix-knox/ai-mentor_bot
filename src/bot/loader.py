from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from src.config import settings

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def setup_routers():
    from src.bot.handlers.start import router as start_router
    from src.bot.handlers.tasks import router as tasks_router
    from src.bot.handlers.habits import router as habits_router
    from src.bot.handlers.journal import router as journal_router
    from src.bot.handlers.ai_chat import router as ai_chat_router
    from src.bot.handlers.profile import router as profile_router
    from src.bot.handlers.learning import router as learning_router
    from src.bot.handlers.playlists import router as playlists_router

    dp.include_router(start_router)
    dp.include_router(tasks_router)
    dp.include_router(habits_router)
    dp.include_router(journal_router)
    dp.include_router(ai_chat_router)
    dp.include_router(profile_router)
    dp.include_router(learning_router)
    dp.include_router(playlists_router)
