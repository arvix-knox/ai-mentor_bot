import re
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.journal_repo import JournalRepository
from src.services.gamification_service import GamificationService


class JournalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.journal_repo = JournalRepository(session)
        self.gamification = GamificationService(session)

    async def create_entry(
        self,
        user_id: int,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> dict:
        if not tags:
            tags = self._extract_tags(content)

        tags = [t.lower().strip().lstrip("#") for t in tags] if tags else []

        entry = await self.journal_repo.create(
            user_id=user_id,
            title=title,
            content=content,
            tags=tags if tags else None,
        )

        xp_event = "journal_entry_long" if len(content) > 500 else "journal_entry"
        total_xp, leveled_up = await self.gamification.award_xp(
            user_id, xp_event, source_type="journal", source_id=entry.id
        )

        return {
            "entry_id": entry.id,
            "title": title,
            "tags": tags,
            "xp_earned": 20 if len(content) > 500 else 10,
            "leveled_up": leveled_up,
        }

    def _extract_tags(self, content: str) -> list[str]:
        tags = re.findall(r"(?<!\#)\#([a-zA-Zа-яА-Я0-9_]+)", content)
        return list(set(tags))

    async def get_entries(
        self,
        user_id: int,
        tag: str | None = None,
        query: str | None = None,
        limit: int = 20,
    ) -> list:
        if query:
            return await self.journal_repo.full_text_search(user_id, query, limit)
        if tag:
            return await self.journal_repo.search_by_tags(user_id, [tag], limit)
        return await self.journal_repo.get_recent(user_id, limit)

    async def get_related(self, entry_id: int, user_id: int) -> list:
        entry = await self.journal_repo.get_by_id(entry_id)
        if not entry or entry.user_id != user_id:
            return []
        if not entry.tags:
            return []
        return await self.journal_repo.find_by_shared_tags(
            user_id, entry.tags, exclude_id=entry_id, limit=5
        )

    async def delete_entry(self, user_id: int, entry_id: int) -> dict:
        entry = await self.journal_repo.get_by_id(entry_id)
        if not entry:
            return {"error": "Entry not found"}
        if entry.user_id != user_id:
            return {"error": "Not your entry"}
        await self.journal_repo.delete(entry_id)
        return {"deleted": True, "title": entry.title}

    @staticmethod
    def format_entry(entry) -> str:
        tags_line = " ".join(f"#{t}" for t in (entry.tags or []))
        return (
            f"📝 *{entry.title}*\n"
            f"_{entry.created_at.strftime('%Y-%m-%d %H:%M')}_\n"
            f"{tags_line}\n\n"
            f"{entry.content}"
        )