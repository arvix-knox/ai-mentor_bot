from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.task_repo import TaskRepository
from src.services.gamification_service import GamificationService, XP_AWARDS
from src.services.achievement_service import AchievementService


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = TaskRepository(session)
        self.gamification = GamificationService(session)
        self.achievement_service = AchievementService(session)

    async def create_task(
        self,
        user_id: int,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        tags: list[str] | None = None,
        project: str | None = None,
        deadline: date | None = None,
        is_recurring: bool = False,
        recurrence_type: str | None = None,
        recurrence_date: date | None = None,
        remind_enabled: bool = False,
        remind_time: str | None = None,
        remind_text: str | None = None,
    ) -> dict:
        task = await self.task_repo.create(
            user_id=user_id, title=title, description=description,
            priority=priority, tags=tags, project=project, deadline=deadline,
            is_recurring=is_recurring, recurrence_type=recurrence_type,
            recurrence_date=recurrence_date, remind_enabled=remind_enabled,
            remind_time=remind_time, remind_text=remind_text,
        )
        await self.gamification.award_xp(user_id, "task_created", source_type="task", source_id=task.id)
        await self.achievement_service.evaluate(user_id)
        return {
            "task_id": task.id,
            "title": task.title,
            "priority": task.priority,
            "deadline": task.deadline,
            "tags": task.tags,
            "is_recurring": task.is_recurring,
            "recurrence_type": task.recurrence_type,
            "remind_enabled": task.remind_enabled,
            "remind_time": task.remind_time,
        }

    async def create_quick_task(
        self,
        user_id: int,
        title: str,
        difficulty: str = "medium",
    ) -> dict:
        difficulty = difficulty if difficulty in ("low", "medium", "high", "critical") else "medium"
        task = await self.task_repo.create(
            user_id=user_id,
            title=title,
            status="done",
            priority=difficulty,
            tags=["useful"],
            completed_at=datetime.utcnow(),
        )
        xp_event = f"task_completed_{difficulty}"
        xp_amount = XP_AWARDS.get(xp_event, 20)
        await self.gamification.award_xp(
            user_id,
            event_type=xp_event,
            xp_amount=xp_amount,
            source_type="quick_task",
            source_id=task.id,
            description=f"Полезная задача: {title}",
        )
        await self.achievement_service.evaluate(user_id)
        return {"task_id": task.id, "title": task.title, "xp_earned": xp_amount}

    async def get_tasks(self, user_id: int, status: str | None = None, tag: str | None = None, limit: int = 50) -> list:
        return await self.task_repo.get_user_tasks(user_id, status, tag, limit)

    async def complete_task(self, user_id: int, task_id: int) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return {"error": "Задача не найдена"}
        if task.user_id != user_id:
            return {"error": "Не твоя задача"}
        if task.status == "done":
            return {"error": "Уже выполнена"}
        task = await self.task_repo.complete_task(task_id)
        xp_event = f"task_completed_{task.priority}"
        xp_amount = XP_AWARDS.get(xp_event, 20)
        total_xp, leveled_up = await self.gamification.award_xp(user_id, xp_event, source_type="task", source_id=task_id)
        bonus = 0
        if task.deadline and task.deadline >= date.today():
            bonus = 15
            await self.gamification.award_xp(user_id, "task_completed_before_deadline", source_type="task", source_id=task_id)
        next_task = await self._create_next_recurring(task)

        new_level = GamificationService.level_from_xp(total_xp)
        unlocked = await self.achievement_service.evaluate(user_id)
        return {
            "title": task.title,
            "xp_earned": xp_amount + bonus,
            "leveled_up": leveled_up,
            "new_level": new_level,
            "next_task_id": next_task.id if next_task else None,
            "next_task_title": next_task.title if next_task else None,
            "achievements": unlocked,
        }

    async def delete_task(self, user_id: int, task_id: int) -> dict:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return {"error": "Не найдена"}
        if task.user_id != user_id:
            return {"error": "Не твоя задача"}
        await self.task_repo.delete(task_id)
        return {"deleted": True, "title": task.title}

    async def _create_next_recurring(self, task):
        if not task.is_recurring or task.recurrence_type is None:
            return None

        base_date = task.deadline or date.today()
        next_deadline: date | None = None
        next_is_recurring = task.is_recurring
        next_type = task.recurrence_type
        next_recur_date = task.recurrence_date

        if task.recurrence_type == "daily":
            next_deadline = base_date + timedelta(days=1)
        elif task.recurrence_type == "weekly":
            next_deadline = base_date + timedelta(days=7)
        elif task.recurrence_type == "monthly":
            next_deadline = base_date + timedelta(days=30)
        elif task.recurrence_type == "on_date":
            if task.recurrence_date:
                next_deadline = task.recurrence_date
            next_is_recurring = False
            next_type = None
            next_recur_date = None

        if not next_deadline:
            return None

        return await self.task_repo.create(
            user_id=task.user_id,
            title=task.title,
            description=task.description,
            status="todo",
            priority=task.priority,
            tags=task.tags,
            project=task.project,
            deadline=next_deadline,
            xp_reward=task.xp_reward,
            is_recurring=next_is_recurring,
            recurrence_type=next_type,
            recurrence_date=next_recur_date,
            remind_enabled=task.remind_enabled,
            remind_time=task.remind_time,
            remind_text=task.remind_text,
        )
