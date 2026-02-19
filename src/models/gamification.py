from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from src.models.base import Base


class XPEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    event_type: Mapped[str] = mapped_column(String(100))
    xp_amount: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(500))

    source_type: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="xp_events")