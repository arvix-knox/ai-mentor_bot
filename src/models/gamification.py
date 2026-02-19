from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from src.models.base import Base


class XPEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    event_type: Mapped[str] = mapped_column(String(100))
    xp_amount: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(500))

    source_type: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="xp_events")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    emoji: Mapped[str] = mapped_column(String(10))
    xp_reward: Mapped[int] = mapped_column(Integer, default=50)
    category: Mapped[str] = mapped_column(String(50))
    condition_type: Mapped[str] = mapped_column(String(50))
    condition_value: Mapped[int] = mapped_column(Integer, default=1)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"))

    unlocked_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")
