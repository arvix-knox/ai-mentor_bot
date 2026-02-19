from sqlalchemy import Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy import func

from src.models.base import Base, TimestampMixin


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_user_created", "user_id", "created_at"),
        Index("ix_journal_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)))

    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    related_entry_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))

    user = relationship("User", back_populates="journal_entries")
    media = relationship(
        "MediaFile", back_populates="journal_entry", cascade="all, delete"
    )


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="SET NULL")
    )

    file_id: Mapped[str] = mapped_column(String(500), nullable=False)
    file_unique_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))
    file_name: Mapped[str | None] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column()
    mime_type: Mapped[str | None] = mapped_column(String(100))

    caption: Mapped[str | None] = mapped_column(String(1024))

    uploaded_at: Mapped[str] = mapped_column(server_default="now()")

    journal_entry = relationship("JournalEntry", back_populates="media")