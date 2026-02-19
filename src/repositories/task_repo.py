from datetime import datetime, date
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.task import Task, TaskLog
from src.repositories.base import BaseRepository


class TaskRepository(BaseRepository):
    model = Task

    async def get_user_tasks(
        self,
        user_id: int,
        status: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[Task]:
        stmt = select(Task).where(Task.user_id == user_id)

        if status:
            stmt = stmt.where(Task.status == status)

        if tag:
            stmt = stmt.where(Task.tags.any(tag))

        stmt = stmt.order_by(Task.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_tasks(
        self, user_id: int, limit: int = 10
    ) -> list[Task]:
        priority_order = func.array_position(
            ["critical", "high", "medium", "low"], Task.priority
        )
        stmt = (
            select(Task)
            .where(
                and_(
                    Task.user_id == user_id,
                    Task.status.in_(["todo", "in_progress"]),
                )
            )
            .order_by(priority_order)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def complete_task(self, task_id: int) -> Task | None:
        task = await self.get_by_id(task_id)
        if not task:
            return None

        old_status = task.status
        task.status = "done"
        task.completed_at = datetime.utcnow()

        log = TaskLog(
            task_id=task_id,
            old_status=old_status,
            new_status="done",
        )
        self.session.add(log)
        await self.session.flush()
        return task

    async def count_created(self, user_id: int, since: datetime) -> int:
        stmt = select(func.count()).where(
            and_(
                Task.user_id == user_id,
                Task.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_completed(self, user_id: int, since: datetime) -> int:
        stmt = select(func.count()).where(
            and_(
                Task.user_id == user_id,
                Task.status == "done",
                Task.completed_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_overdue(self, user_id: int) -> int:
        stmt = select(func.count()).where(
            and_(
                Task.user_id == user_id,
                Task.status.in_(["todo", "in_progress"]),
                Task.deadline < date.today(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def get_completion_rate(
        self, user_id: int, since: datetime
    ) -> float:
        total = await self.count_created(user_id, since)
        if total == 0:
            return 0.0
        completed = await self.count_completed(user_id, since)
        return completed / total