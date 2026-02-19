from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str

    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    AI_BACKEND: str = "groq"

    ALLOWED_TELEGRAM_IDS: str = ""
    ADMIN_TELEGRAM_ID: int = 0

    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "Europe/Moscow"

    @property
    def allowed_ids(self) -> set[int]:
        if not self.ALLOWED_TELEGRAM_IDS:
            return set()
        return {int(x.strip()) for x in self.ALLOWED_TELEGRAM_IDS.split(",")}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()