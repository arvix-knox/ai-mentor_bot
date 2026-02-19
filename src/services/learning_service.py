from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.learning_repo import LearningRepository
from src.services.gamification_service import GamificationService


DEFAULT_SUGGESTIONS = {
    "fastapi": [
        {
            "resource_type": "article",
            "title": "FastAPI: Практический гайд по созданию API",
            "url": "https://habr.com/ru/search/?q=fastapi",
            "description": "Подборка Habr-статей по FastAPI.",
            "topic": "FastAPI",
        },
        {
            "resource_type": "course",
            "title": "Roadmap: FastAPI от 0 до deploy",
            "url": "https://www.youtube.com/results?search_query=fastapi+tutorial+ru",
            "description": "Подборка видеокурсов и туториалов.",
            "topic": "FastAPI",
        },
    ],
    "python": [
        {
            "resource_type": "article",
            "title": "Python backend best practices",
            "url": "https://habr.com/ru/search/?q=python%20backend",
            "description": "Лучшие практики backend-разработки на Python.",
            "topic": "Python",
        },
        {
            "resource_type": "video",
            "title": "Python backend architecture",
            "url": "https://www.youtube.com/results?search_query=python+backend+architecture",
            "description": "Видео по архитектуре сервисов.",
            "topic": "Python",
        },
    ],
}


class LearningService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LearningRepository(session)
        self.gamification = GamificationService(session)

    async def add_resource(
        self,
        user_id: int,
        resource_type: str,
        title: str,
        url: str | None = None,
        description: str | None = None,
        topic: str | None = None,
    ) -> dict:
        resource = await self.repo.create(
            user_id=user_id,
            resource_type=resource_type,
            title=title,
            url=url,
            description=description,
            topic=topic,
        )
        await self.gamification.award_xp(
            user_id,
            event_type="learning_resource_added",
            xp_amount=8,
            source_type="learning",
            source_id=resource.id,
        )
        return {"resource_id": resource.id, "title": resource.title}

    async def mark_done(self, user_id: int, resource_id: int) -> dict:
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            return {"error": "Ресурс не найден"}
        if resource.user_id != user_id:
            return {"error": "Не твой ресурс"}
        if resource.is_completed:
            return {"already_done": True, "title": resource.title}

        resource = await self.repo.mark_completed(resource_id)
        await self.gamification.award_xp(
            user_id,
            event_type="learning_resource_completed",
            xp_amount=25,
            source_type="learning",
            source_id=resource.id,
        )
        return {"done": True, "title": resource.title}

    async def get_user_resources(self, user_id: int, completed: bool | None = None):
        return await self.repo.get_user_resources(user_id, completed=completed)

    async def suggest(self, topic: str) -> list[dict]:
        key = (topic or "").strip().lower()
        if not key:
            return []
        if key in DEFAULT_SUGGESTIONS:
            return DEFAULT_SUGGESTIONS[key]

        return [
            {
                "resource_type": "article",
                "title": f"Habr: подборка по теме '{topic}'",
                "url": f"https://habr.com/ru/search/?q={topic}",
                "description": "Статьи по теме.",
                "topic": topic,
            },
            {
                "resource_type": "video",
                "title": f"YouTube: видео по теме '{topic}'",
                "url": f"https://www.youtube.com/results?search_query={topic}",
                "description": "Видео и разборы.",
                "topic": topic,
            },
            {
                "resource_type": "course",
                "title": f"Курс по теме '{topic}'",
                "url": f"https://www.google.com/search?q={topic}+course",
                "description": "Курсы и туториалы.",
                "topic": topic,
            },
        ]
