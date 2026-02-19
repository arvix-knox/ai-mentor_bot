from sqlalchemy import BigInteger, String, Integer, Boolean, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))

    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    total_xp_earned: Mapped[int] = mapped_column(Integer, default=0)

    ai_mode: Mapped[str] = mapped_column(String(20), default="adaptive")

    tech_stack: Mapped[str | None] = mapped_column(Text)
    goals: Mapped[str | None] = mapped_column(Text)
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