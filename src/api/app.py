import json
import re
from datetime import date
from pathlib import Path
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from src.core.database import async_session_factory
from src.repositories.user_repo import UserRepository
from src.repositories.task_repo import TaskRepository
from src.repositories.habit_repo import HabitRepository
from src.repositories.playlist_repo import PlaylistRepository
from src.services.task_service import TaskService
from src.services.habit_service import HabitService
from src.services.ai_service import AIService
from src.services.achievement_service import AchievementService
from src.services.learning_service import LearningService
from src.services.playlist_service import PlaylistService
from src.services.data_cleanup_service import DataCleanupService


BASE_DIR = Path(__file__).resolve().parents[2]
WEBAPP_DIR = BASE_DIR / "webapp"


class TelegramUserPayload(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str = "Пользователь"
    last_name: str | None = None


class BootstrapRequest(TelegramUserPayload):
    pass


class TaskCreatePayload(BaseModel):
    telegram_id: int
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: str = "medium"
    tags: list[str] | None = None
    deadline: date | None = None
    is_recurring: bool = False
    recurrence_type: str | None = None
    recurrence_date: date | None = None
    remind_enabled: bool = False
    remind_time: str | None = None
    remind_text: str | None = None


class QuickTaskPayload(BaseModel):
    telegram_id: int
    title: str
    difficulty: str = "medium"


class CompleteTaskPayload(BaseModel):
    telegram_id: int


class HabitCreatePayload(BaseModel):
    telegram_id: int
    name: str = Field(min_length=1, max_length=255)
    emoji: str = "✅"
    description: str | None = None
    remind_enabled: bool = True
    remind_time: str | None = "21:00"
    remind_text: str | None = None


class MentorChatPayload(BaseModel):
    telegram_id: int
    message: str


class ProfileUpdatePayload(BaseModel):
    telegram_id: int
    display_name: str | None = None
    tech_stack: list[str] | None = None
    goals: list[str] | None = None
    knowledge_level: str | None = None
    mentor_name: str | None = None
    mentor_persona: str | None = None


class SettingsUpdatePayload(BaseModel):
    telegram_id: int
    patch: dict


class CleanupPayload(BaseModel):
    telegram_id: int
    period: str = "week"


class LearningCreatePayload(BaseModel):
    telegram_id: int
    resource_type: str
    title: str
    url: str | None = None
    description: str | None = None
    topic: str | None = None


class PlaylistCreatePayload(BaseModel):
    telegram_id: int
    name: str
    emoji: str = "🎵"


class PlaylistTrackPayload(BaseModel):
    telegram_id: int
    title: str
    performer: str | None = None
    url: str | None = None
    duration: int | None = None


app = FastAPI(title="Mentor Bot WebApp API", version="1.0.0")
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if WEBAPP_DIR.exists():
    app.mount("/webapp/assets", StaticFiles(directory=str(WEBAPP_DIR)), name="webapp_assets")


async def _get_user(session, payload: TelegramUserPayload):
    repo = UserRepository(session)
    return await repo.get_or_create(
        telegram_id=payload.telegram_id,
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )


def _serialize_task(task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "tags": task.tags or [],
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "is_recurring": task.is_recurring,
        "recurrence_type": task.recurrence_type,
        "recurrence_date": task.recurrence_date.isoformat() if task.recurrence_date else None,
        "remind_enabled": task.remind_enabled,
        "remind_time": task.remind_time,
        "remind_text": task.remind_text,
    }


def _serialize_habit(habit) -> dict:
    return {
        "id": habit.id,
        "name": habit.name,
        "emoji": habit.emoji,
        "current_streak": habit.current_streak,
        "best_streak": habit.best_streak,
        "total_completions": habit.total_completions,
        "schedule_mask": habit.schedule_mask,
        "remind_enabled": habit.remind_enabled,
        "remind_time": habit.remind_time,
        "remind_text": habit.remind_text,
    }


def _serialize_user(user) -> dict:
    settings_data = user.get_settings()
    tech_stack = []
    goals_data = {}
    if user.tech_stack:
        try:
            tech_stack = json.loads(user.tech_stack)
        except Exception:
            tech_stack = []
    if user.goals:
        try:
            goals_data = json.loads(user.goals)
        except Exception:
            goals_data = {}

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "display_name": user.get_display_name(),
        "first_name": user.first_name,
        "level": user.level,
        "xp": user.xp,
        "total_xp_earned": user.total_xp_earned,
        "ai_mode": user.ai_mode,
        "timezone": user.timezone,
        "discipline_score": user.discipline_score,
        "growth_score": user.growth_score,
        "tech_stack": tech_stack,
        "goals": goals_data.get("goals", []),
        "knowledge_level": goals_data.get("knowledge_level"),
        "settings": settings_data,
    }


def _parse_time_from_text(text: str) -> str | None:
    match = re.search(r"\b([01]\d|2[0-3]):([0-5]\d)\b", text or "")
    if not match:
        return None
    return f"{match.group(1)}:{match.group(2)}"


@app.on_event("startup")
async def startup():
    try:
        async with async_session_factory() as session:
            await AchievementService(session).ensure_catalog()
            await session.commit()
    except Exception as e:
        logger.warning("Startup DB init skipped: %s", e)


def _is_db_connectivity_error(exc: Exception) -> bool:
    text = str(exc).lower()
    patterns = (
        "connection_lost",
        "cannot connect",
        "connection refused",
        "connection reset",
        "targetserverattributenotmatched",
        "asyncpg",
        "database",
        "ssl",
    )
    return any(p in text for p in patterns)


def _flatten_exceptions(exc: BaseException) -> list[BaseException]:
    if isinstance(exc, BaseExceptionGroup):
        flat: list[BaseException] = []
        for inner in exc.exceptions:
            flat.extend(_flatten_exceptions(inner))
        return flat
    return [exc]


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request, exc: SQLAlchemyError):
    from fastapi.responses import JSONResponse
    logger.error("DB error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "База данных недоступна. Проверь DATABASE_URL и сеть к БД."},
    )


@app.exception_handler(ExceptionGroup)
async def exception_group_handler(request, exc: ExceptionGroup):
    from fastapi.responses import JSONResponse
    errors = _flatten_exceptions(exc)
    db_related = any(
        isinstance(err, SQLAlchemyError) or _is_db_connectivity_error(Exception(str(err)))
        for err in errors
    )
    if db_related:
        logger.error("Connectivity error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Сервер/БД недоступны по сети. Запусти локальную БД или проверь интернет/VPN.",
            },
        )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.exception_handler(ConnectionError)
async def connection_error_handler(request, exc: ConnectionError):
    from fastapi.responses import JSONResponse
    logger.error("Connection error on %s %s: %s", request.method, request.url.path, exc)
    if _is_db_connectivity_error(exc):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Сервер/БД недоступны по сети. Запусти локальную БД или проверь интернет/VPN.",
            },
        )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/")
async def webapp_index():
    return await open_webapp()


@app.get("/webapp")
async def open_webapp():
    index = WEBAPP_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="webapp/index.html not found")
    return FileResponse(index)


@app.post("/api/v1/bootstrap")
async def bootstrap(payload: BootstrapRequest):
    async with async_session_factory() as session:
        user = await _get_user(session, payload)
        task_repo = TaskRepository(session)
        habit_repo = HabitRepository(session)
        achievement_service = AchievementService(session)
        learning_service = LearningService(session)
        playlist_service = PlaylistService(session)

        await achievement_service.evaluate(user.id)
        tasks = await task_repo.get_user_tasks(user.id, limit=100)
        habits = await habit_repo.get_active_habits(user.id)
        achievements = await achievement_service.get_user_achievements(user.id)
        resources = await learning_service.get_user_resources(user.id)
        playlists = await playlist_service.get_user_playlists(user.id)

        await session.commit()

        return {
            "user": _serialize_user(user),
            "tasks": [_serialize_task(t) for t in tasks],
            "habits": [_serialize_habit(h) for h in habits],
            "achievements": [
                {
                    "code": a.code,
                    "name": a.name,
                    "description": a.description,
                    "emoji": a.emoji,
                    "xp_reward": a.xp_reward,
                }
                for a in achievements
            ],
            "resources": [
                {
                    "id": r.id,
                    "resource_type": r.resource_type,
                    "title": r.title,
                    "url": r.url,
                    "description": r.description,
                    "topic": r.topic,
                    "is_completed": r.is_completed,
                }
                for r in resources
            ],
            "playlists": [{"id": p.id, "name": p.name, "emoji": p.emoji} for p in playlists],
        }


@app.patch("/api/v1/profile")
async def update_profile(payload: ProfileUpdatePayload):
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        updates = {}
        if payload.display_name is not None:
            updates["display_name"] = payload.display_name.strip()[:50]

        if payload.tech_stack is not None:
            clean_stack = [s.strip() for s in payload.tech_stack if s.strip()]
            updates["tech_stack"] = json.dumps(clean_stack, ensure_ascii=False)

        goals_data = {}
        if user.goals:
            try:
                goals_data = json.loads(user.goals)
            except Exception:
                goals_data = {}
        if payload.goals is not None:
            goals_data["goals"] = [g.strip() for g in payload.goals if g.strip()]
        if payload.knowledge_level is not None:
            goals_data["knowledge_level"] = payload.knowledge_level
        if payload.goals is not None or payload.knowledge_level is not None:
            updates["goals"] = json.dumps(goals_data, ensure_ascii=False)

        settings_data = user.get_settings()
        if payload.mentor_name is not None:
            settings_data["mentor_name"] = payload.mentor_name[:50]
        if payload.mentor_persona is not None:
            settings_data["mentor_persona"] = payload.mentor_persona
        if payload.mentor_name is not None or payload.mentor_persona is not None:
            updates["settings_json"] = user.save_settings(settings_data)

        if updates:
            await user_repo.update(user.id, **updates)
            user = await user_repo.get_by_id(user.id)

        await session.commit()
        return {"ok": True, "user": _serialize_user(user)}


@app.get("/api/v1/settings")
async def get_settings(telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"settings": user.get_settings()}


@app.patch("/api/v1/settings")
async def patch_settings(payload: SettingsUpdatePayload):
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        settings_data = user.get_settings()
        for key, value in payload.patch.items():
            if isinstance(value, dict) and isinstance(settings_data.get(key), dict):
                settings_data[key].update(value)
            else:
                settings_data[key] = value
        await repo.update(user.id, settings_json=user.save_settings(settings_data))
        await session.commit()
        return {"ok": True, "settings": settings_data}


@app.post("/api/v1/tasks")
async def create_task(payload: TaskCreatePayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        settings_data = user.get_settings()
        remind_text = payload.remind_text
        if payload.remind_enabled and not remind_text:
            tmpl = settings_data.get("notifications", {}).get("remind_text_template", "🔔 Пора: {name}")
            remind_text = tmpl.format(name=payload.title)

        data = payload.model_dump()
        data.pop("telegram_id")
        data["remind_text"] = remind_text
        result = await TaskService(session).create_task(user_id=user.id, **data)
        await session.commit()
        return result


@app.get("/api/v1/tasks")
async def list_tasks(telegram_id: int, status: str | None = None):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        tasks = await TaskService(session).get_tasks(user.id, status=status, limit=200)
        return {"tasks": [_serialize_task(t) for t in tasks]}


@app.post("/api/v1/tasks/quick")
async def create_quick_task(payload: QuickTaskPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await TaskService(session).create_quick_task(
            user_id=user.id,
            title=payload.title,
            difficulty=payload.difficulty,
        )
        await session.commit()
        return result


@app.post("/api/v1/tasks/{task_id}/complete")
async def complete_task(task_id: int, payload: CompleteTaskPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await TaskService(session).complete_task(user.id, task_id)
        await session.commit()
        return result


@app.post("/api/v1/habits")
async def create_habit(payload: HabitCreatePayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        result = await HabitService(session).create_habit(
            user_id=user.id,
            name=payload.name,
            emoji=payload.emoji,
            description=payload.description,
            remind_enabled=payload.remind_enabled,
            remind_time=payload.remind_time,
            remind_text=payload.remind_text,
        )
        await session.commit()
        return result


@app.get("/api/v1/habits")
async def list_habits(telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        habits = await HabitService(session).get_user_habits(user.id)
        return {"habits": [_serialize_habit(h) for h in habits]}


@app.post("/api/v1/habits/{habit_id}/check")
async def check_habit(habit_id: int, payload: CompleteTaskPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await HabitService(session).log_completion(user.id, habit_id)
        await session.commit()
        return result


@app.get("/api/v1/achievements")
async def achievements(telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        svc = AchievementService(session)
        await svc.evaluate(user.id)
        rows = await svc.get_user_achievements(user.id)
        await session.commit()
        return {
            "achievements": [
                {
                    "code": a.code,
                    "name": a.name,
                    "description": a.description,
                    "emoji": a.emoji,
                    "xp_reward": a.xp_reward,
                }
                for a in rows
            ]
        }


@app.post("/api/v1/mentor/chat")
async def mentor_chat(payload: MentorChatPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        text = payload.message.strip()
        settings_data = user.get_settings()
        ai_perms = settings_data.get("ai_permissions", {})

        if text.lower().startswith("добавь задачу") and ai_perms.get("create_tasks", True):
            title = text[len("добавь задачу"):].strip(" :.-")
            if not title:
                return {"reply": "Напиши так: `добавь задачу <название> [HH:MM]`"}
            remind_time = _parse_time_from_text(title)
            title_clean = re.sub(r"\b([01]\d|2[0-3]):([0-5]\d)\b", "", title).strip()
            task_result = await TaskService(session).create_task(
                user_id=user.id,
                title=title_clean,
                priority="medium",
                remind_enabled=bool(remind_time),
                remind_time=remind_time,
                remind_text=f"🔔 Пора выполнять: {title_clean}",
            )
            await session.commit()
            return {"reply": f"✅ Задача создана: {task_result['title']}"}

        ai = AIService(session)
        response, ms = await ai.get_response(user.id, text)
        await session.commit()
        return {"reply": response, "response_time_ms": ms}


@app.get("/api/v1/mentor/today-plan")
async def mentor_today_plan(telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        ai = AIService(session)
        response = await ai.generate_today_plan(user.id, user=user)
        await session.commit()
        return {"reply": response}


@app.get("/api/v1/learning")
async def list_learning(telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        rows = await LearningService(session).get_user_resources(user.id)
        return {
            "resources": [
                {
                    "id": r.id,
                    "resource_type": r.resource_type,
                    "title": r.title,
                    "url": r.url,
                    "description": r.description,
                    "topic": r.topic,
                    "is_completed": r.is_completed,
                }
                for r in rows
            ]
        }


@app.post("/api/v1/learning")
async def create_learning(payload: LearningCreatePayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await LearningService(session).add_resource(
            user_id=user.id,
            resource_type=payload.resource_type,
            title=payload.title,
            url=payload.url,
            description=payload.description,
            topic=payload.topic,
        )
        await AchievementService(session).evaluate(user.id)
        await session.commit()
        return result


@app.post("/api/v1/learning/{resource_id}/done")
async def complete_learning(resource_id: int, payload: CompleteTaskPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await LearningService(session).mark_done(user.id, resource_id)
        await AchievementService(session).evaluate(user.id)
        await session.commit()
        return result


@app.get("/api/v1/learning/suggest")
async def suggest_learning(topic: str):
    async with async_session_factory() as session:
        items = await LearningService(session).suggest(topic)
        return {"suggestions": items}


@app.get("/api/v1/playlists")
async def list_playlists(telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        rows = await PlaylistService(session).get_user_playlists(user.id)
        return {"playlists": [{"id": p.id, "name": p.name, "emoji": p.emoji} for p in rows]}


@app.post("/api/v1/playlists")
async def create_playlist(payload: PlaylistCreatePayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await PlaylistService(session).create_playlist(
            user_id=user.id,
            name=payload.name,
            emoji=payload.emoji,
        )
        await AchievementService(session).evaluate(user.id)
        await session.commit()
        return result


@app.get("/api/v1/playlists/{playlist_id}")
async def get_playlist(playlist_id: int, telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        playlist, tracks = await PlaylistService(session).get_playlist_tracks(user.id, playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {
            "playlist": {"id": playlist.id, "name": playlist.name, "emoji": playlist.emoji},
            "tracks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "performer": t.performer,
                    "file_id": t.file_id,
                    "duration": t.duration,
                    "position": t.position,
                }
                for t in tracks
            ],
        }


@app.post("/api/v1/playlists/{playlist_id}/tracks")
async def add_playlist_track(playlist_id: int, payload: PlaylistTrackPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        file_id = payload.url or f"track://{uuid4()}"
        result = await PlaylistService(session).add_track(
            user_id=user.id,
            playlist_id=playlist_id,
            file_id=file_id,
            file_unique_id=str(uuid4()),
            title=payload.title,
            performer=payload.performer,
            duration=payload.duration,
        )
        await AchievementService(session).evaluate(user.id)
        await session.commit()
        return result


@app.delete("/api/v1/playlists/{playlist_id}")
async def delete_playlist(playlist_id: int, telegram_id: int):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await PlaylistService(session).delete_playlist(user.id, playlist_id)
        await session.commit()
        return result


@app.post("/api/v1/cleanup/history")
async def cleanup_history(payload: CleanupPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await DataCleanupService(session).cleanup_history(user.id, payload.period)
        await session.commit()
        return result


@app.post("/api/v1/cleanup/profile")
async def cleanup_profile(payload: CompleteTaskPayload):
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(payload.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        result = await DataCleanupService(session).delete_profile(user.id)
        await session.commit()
        return result
