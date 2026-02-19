from datetime import date, datetime
from sqlalchemy import Integer, String, Boolean, ForeignKey, Date, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from src.models.base import Base, TimestampMixin


class Habit(Base, TimestampMixin):
    __tablename__ = "habits"
    __table_args__ = (
        Index("ix_habits_user_active", "user_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    emoji: Mapped[str] = mapped_column(String(10), default="✅")

    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_completions: Mapped[int] = mapped_column(Integer, default=0)

    streak_freezes_available: Mapped[int] = mapped_column(Integer, default=1)
    streak_freezes_used: Mapped[int] = mapped_column(Integer, default=0)

    schedule_mask: Mapped[int] = mapped_column(Integer, default=127)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    xp_per_completion: Mapped[int] = mapped_column(Integer, default=15)

    user = relationship("User", back_populates="habits")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete")


class HabitLog(Base):
    __tablename__ = "habit_logs"
    __table_args__ = (
        Index("ix_habit_logs_habit_date", "habit_id", "log_date", unique=True),
        Index("ix_habit_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    habit_id: Mapped[int] = mapped_column(
        ForeignKey("habits.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    is_freeze: Mapped[bool] = mapped_column(Boolean, default=False)

    logged_at: Mapped[datetime] = mapped_column(server_default=func.now())

    habit = relationship("Habit", back_populates="logs")