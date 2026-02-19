from datetime import date, timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.task_repo import TaskRepository
from src.repositories.journal_repo import JournalRepository
from src.repositories.xp_repo import XPRepository
from src.repositories.user_repo import UserRepository
from src.services.gamification_service import GamificationService
from src.services.habit_service import HabitService
from src.services.ai_service import AIService
from src.models.ai_memory import WeeklyReport


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = TaskRepository(session)
        self.journal_repo = JournalRepository(session)
        self.xp_repo = XPRepository(session)
        self.user_repo = UserRepository(session)
        self.gamification = GamificationService(session)
        self.habit_service = HabitService(session)
        self.ai_service = AIService(session)

    async def generate_weekly_report(self, user_id: int) -> dict:
        today = date.today()
        week_start = today - timedelta(days=6)
        since = datetime.combine(week_start, datetime.min.time())

        tasks_created = await self.task_repo.count_created(user_id, since)
        tasks_completed = await self.task_repo.count_completed(user_id, since)
        tasks_overdue = await self.task_repo.count_overdue(user_id)

        habit_perf = await self.habit_service.get_weekly_performance(user_id)

        journal_count = await self.journal_repo.count_entries(user_id, since)

        xp_earned = await self.xp_repo.sum_positive_xp(user_id, since)
        xp_lost = await self.xp_repo.sum_negative_xp(user_id, since)

        discipline = await self.gamification.calculate_discipline_score(user_id)
        growth = await self.gamification.calculate_growth_score(user_id)

        metrics = {
            "tasks_created": tasks_created,
            "tasks_completed": tasks_completed,
            "tasks_overdue": tasks_overdue,
            "habit_rate": habit_perf["overall_rate"],
            "best_streak": habit_perf["best_streak"],
            "journal_count": journal_count,
            "xp_earned": xp_earned,
            "xp_lost": abs(xp_lost),
            "discipline": discipline,
            "growth": growth,
        }

        ai_review = await self.ai_service.generate_weekly_review(user_id, metrics)

        report = WeeklyReport(
            user_id=user_id,
            week_start=week_start,
            week_end=today,
            tasks_created=tasks_created,
            tasks_completed=tasks_completed,
            tasks_overdue=tasks_overdue,
            habits_total_possible=habit_perf["total_possible"],
            habits_completed=habit_perf["total_completed"],
            habit_completion_rate=habit_perf["overall_rate"],
            journal_entries_count=journal_count,
            xp_earned=xp_earned,
            xp_lost=abs(xp_lost),
            discipline_score=discipline,
            growth_score=growth,
            ai_review=ai_review,
            best_streak=habit_perf["best_streak"],
        )
        self.session.add(report)
        await self.session.flush()

        return {**metrics, "ai_review": ai_review, "habits": habit_perf["habits"]}

    @staticmethod
    def format_weekly_report(data: dict) -> str:
        d = data["discipline"]
        d_emoji = "🟢" if d >= 70 else ("🟡" if d >= 40 else "🔴")

        g = data["growth"]
        g_emoji = "🟢" if g >= 70 else ("🟡" if g >= 40 else "🔴")

        habit_lines = []
        for h in data.get("habits", []):
            filled = int(h["rate"] * 10)
            bar = "▓" * filled + "░" * (10 - filled)
            habit_lines.append(
                f"  {h['emoji']} {h['name']}: [{bar}] {h['rate']:.0%} "
                f"(🔥{h['streak']}d)"
            )
        habits_text = "\n".join(habit_lines) if habit_lines else "  No habits"

        return (
            f"📊 *WEEKLY REVIEW*\n"
            f"{'═' * 30}\n\n"
            f"📋 *Tasks*\n"
            f"  Created: {data['tasks_created']}\n"
            f"  Completed: {data['tasks_completed']}\n"
            f"  Overdue: {data['tasks_overdue']} "
            f"{'⚠️' if data['tasks_overdue'] > 0 else '✅'}\n\n"
            f"🔄 *Habits* ({data['habit_rate']:.0%} overall)\n"
            f"{habits_text}\n\n"
            f"📝 *Journal*: {data['journal_count']} entries\n\n"
            f"⭐ *XP*: +{data['xp_earned']} / -{data['xp_lost']}\n\n"
            f"{d_emoji} *Discipline*: {data['discipline']:.0f}/100\n"
            f"{g_emoji} *Growth*: {data['growth']:.0f}/100\n\n"
            f"{'═' * 30}\n"
            f"🤖 *AI Review:*\n"
            f"{data['ai_review']}"
        )