from datetime import date, datetime
from sqlalchemy import Integer, String, Text, ForeignKey, Date, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import func

from src.models.base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_user_deadline", "user_id", "deadline"),
        Index("ix_tasks_user_priority", "user_id", "priority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)))
    project: Mapped[str | None] = mapped_column(String(255))

    deadline: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column()

    xp_reward: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship("User", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete")


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE")
    )
    old_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50))
    changed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    task = relationship("Task", back_populates="logs")