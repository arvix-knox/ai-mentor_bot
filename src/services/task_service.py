from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.task_repo import TaskRepository
from src.services.gamification_service import GamificationService


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = TaskRepository(session)
        self.gamification = GamificationService(session)

    async def create_task(
        self,
        user_id: int,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        tags: list[str] | None = None,
        project: str | None = None,
        deadline: date | None = None,
    ) -> dict:
        task = await self.task_repo.create(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            tags=tags,
            project=project,
            deadline=deadline,
        )

        await self.gamification.award_xp(
            user_id, "task_created", source_type="task", source_id=task.id
        )

        return {
            "task_id": task.id,
            "title": task.title,
            "priority": task.priority,
            "deadline": task.deadline,
            "tags": task.tags,
        }

    async def get_tasks(
        self,
        user_id: int,
        status: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list:
        return await self.task_repo.get_user_tasks(user_id, status, tag, limit)

    async def complete_task(self, user_id: int, task_id: int) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return {"error": "Task not found"}

        if task.user_id != user_id:
            return {"error": "Not your task"}

        if task.status == "done":
            return {"error": "Task already completed"}

        task = await self.task_repo.complete_task(task_id)

        xp_event = f"task_completed_{task.priority}"
        total_xp, leveled_up = await self.gamification.award_xp(
            user_id, xp_event, source_type="task", source_id=task_id
        )

        bonus_xp = 0
        if task.deadline and task.deadline >= date.today():
            bonus_xp = 15
            await self.gamification.award_xp(
                user_id,
                "task_completed_before_deadline",
                source_type="task",
                source_id=task_id,
            )

        new_level = GamificationService.level_from_xp(total_xp)

        return {
            "title": task.title,
            "xp_earned": (
                GamificationService.XP_AWARDS if hasattr(GamificationService, 'XP_AWARDS')
                else {"task_completed_medium": 20}
            ).get(xp_event, 20) + bonus_xp,
            "leveled_up": leveled_up,
            "new_level": new_level,
        }

    async def delete_task(self, user_id: int, task_id: int) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return {"error": "Task not found"}

        if task.user_id != user_id:
            return {"error": "Not your task"}

        await self.task_repo.delete(task_id)
        return {"deleted": True, "title": task.title}