import json
from sqlalchemy import BigInteger, String, Integer, Boolean, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))

    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    total_xp_earned: Mapped[int] = mapped_column(Integer, default=0)

    ai_mode: Mapped[str] = mapped_column(String(20), default="adaptive")

    tech_stack: Mapped[str | None] = mapped_column(Text)
    goals: Mapped[str | None] = mapped_column(Text)
    settings_json: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")

    discipline_score: Mapped[float] = mapped_column(Float, default=50.0)
    growth_score: Mapped[float] = mapped_column(Float, default=50.0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tasks = relationship("Task", back_populates="user", lazy="selectin")
    habits = relationship("Habit", back_populates="user", lazy="selectin")
    journal_entries = relationship("JournalEntry", back_populates="user")
    xp_events = relationship("XPEvent", back_populates="user")
    memory_summaries = relationship("AIMemorySummary", back_populates="user")
    weekly_reports = relationship("WeeklyReport", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    playlists = relationship("Playlist", back_populates="user")
    resources = relationship("LearningResource", back_populates="user")

    def get_display_name(self) -> str:
        return self.display_name or self.first_name

    def get_settings(self) -> dict:
        defaults = {
            "notifications": {
                "morning": True, "evening": True, "motivation": True,
                "streak": True, "weekly": True,
                "morning_time": "08:00", "evening_time": "21:00",
                "task_remind_default": True, "habit_remind_default": True,
                "remind_text_template": "🔔 Пора: {name}",
            },
            "ai_permissions": {
                "read_tasks": True, "read_habits": True, "read_journal": True,
                "read_stats": True, "create_tasks": True, "modify_tasks": True,
                "read_resources": True,
            },
            "ai_daily_brief": True,
            "ai_journal_review": True,
            "knowledge_level": "beginner",
        }
        if self.settings_json:
            try:
                saved = json.loads(self.settings_json)
                for k, v in saved.items():
                    if isinstance(v, dict) and isinstance(defaults.get(k), dict):
                        defaults[k].update(v)
                    else:
                        defaults[k] = v
            except Exception:
                pass
        return defaults

    def save_settings(self, settings: dict) -> str:
        return json.dumps(settings, ensure_ascii=False)
