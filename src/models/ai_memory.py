from datetime import datetime, date
from sqlalchemy import Integer, String, Text, ForeignKey, Date, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from src.models.base import Base


class AIMemorySummary(Base):
    __tablename__ = "ai_memory_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    summary_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text, nullable=False)

    token_count: Mapped[int] = mapped_column(Integer, default=0)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="memory_summaries")


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    user_message: Mapped[str] = mapped_column(Text)
    ai_response: Mapped[str] = mapped_column(Text)
    ai_mode: Mapped[str] = mapped_column(String(50))

    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    token_count_prompt: Mapped[int | None] = mapped_column(Integer)
    token_count_response: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    week_start: Mapped[date] = mapped_column(Date)
    week_end: Mapped[date] = mapped_column(Date)

    tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_overdue: Mapped[int] = mapped_column(Integer, default=0)

    habits_total_possible: Mapped[int] = mapped_column(Integer, default=0)
    habits_completed: Mapped[int] = mapped_column(Integer, default=0)
    habit_completion_rate: Mapped[float] = mapped_column(Float, default=0.0)

    journal_entries_count: Mapped[int] = mapped_column(Integer, default=0)

    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    xp_lost: Mapped[int] = mapped_column(Integer, default=0)

    discipline_score: Mapped[float] = mapped_column(Float, default=0.0)
    growth_score: Mapped[float] = mapped_column(Float, default=0.0)

    ai_review: Mapped[str | None] = mapped_column(Text)

    best_streak: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="weekly_reports")