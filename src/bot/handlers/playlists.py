from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.playlist_service import PlaylistService
from src.services.achievement_service import AchievementService
from src.bot.keyboards.inline import (
    playlists_menu_keyboard,
    playlist_list_keyboard,
    playlist_item_keyboard,
    back_keyboard,
)

router = Router()


class PlaylistStates(StatesGroup):
    waiting_name = State()
    waiting_track = State()


@router.message(Command("playlist"))
async def cmd_playlist(message: Message):
    await message.answer("🎵 *Плейлисты*", reply_markup=playlists_menu_keyboard())


@router.callback_query(F.data == "menu:playlists")
async def cb_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🎵 *Плейлисты*", reply_markup=playlists_menu_keyboard())
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(F.text == "🎵 Плейлисты")
async def reply_playlist(message: Message):
    await message.answer("🎵 *Плейлисты*", reply_markup=playlists_menu_keyboard())


@router.callback_query(F.data == "plist:add")
async def cb_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PlaylistStates.waiting_name)
    await callback.message.edit_text("Отправь название плейлиста (можно с эмодзи в начале):")
    await callback.answer()


@router.message(PlaylistStates.waiting_name)
async def st_name(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    raw = (message.text or "").strip()
    emoji = "🎵"
    name = raw
    if raw and not raw[0].isalnum():
        emoji = raw[0]
        name = raw[1:].strip() or "Плейлист"
    result = await PlaylistService(session).create_playlist(db_user.id, name=name[:255], emoji=emoji)
    await AchievementService(session).evaluate(db_user.id)
    await message.answer(f"✅ {emoji} *{result['name']}* создан", reply_markup=playlists_menu_keyboard())
    await state.clear()


@router.callback_query(F.data == "plist:list")
async def cb_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    rows = await PlaylistService(session).get_user_playlists(db_user.id)
    if not rows:
        try:
            await callback.message.edit_text("🎵 Плейлистов пока нет", reply_markup=playlists_menu_keyboard())
        except TelegramBadRequest:
            pass
        await callback.answer()
        return
    try:
        await callback.message.edit_text("🎵 *Твои плейлисты*", reply_markup=playlist_list_keyboard(rows))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("plist:view:"))
async def cb_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    pid = int(callback.data.split(":")[2])
    playlist, tracks = await PlaylistService(session).get_playlist_tracks(db_user.id, pid)
    if not playlist:
        await callback.answer("Не найден")
        return
    lines = []
    for t in tracks[:12]:
        title = t.title or "Без названия"
        performer = f" — {t.performer}" if t.performer else ""
        lines.append(f"{t.position}. {title}{performer}")
    tracks_text = "\n".join(lines) if lines else "Пока без треков"
    text = f"{playlist.emoji} *{playlist.name}*\n\n🎶 {tracks_text}"
    try:
        await callback.message.edit_text(text, reply_markup=playlist_item_keyboard(pid))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("plist:add_track:"))
async def cb_add_track(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.split(":")[2])
    await state.set_state(PlaylistStates.waiting_track)
    await state.update_data(track_playlist_id=pid)
    await callback.message.edit_text(
        "Отправь аудио-файл или текст в формате:\n`Название | Исполнитель | URL`",
        reply_markup=back_keyboard(f"plist:view:{pid}"),
    )
    await callback.answer()


@router.message(PlaylistStates.waiting_track, F.audio)
async def st_track_audio(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = await state.get_data()
    pid = data.get("track_playlist_id")
    audio = message.audio
    result = await PlaylistService(session).add_track(
        user_id=db_user.id,
        playlist_id=pid,
        file_id=audio.file_id,
        file_unique_id=audio.file_unique_id,
        title=audio.title or audio.file_name or "Track",
        performer=audio.performer,
        duration=audio.duration,
    )
    if result.get("error"):
        await message.answer(f"❌ {result['error']}")
        return
    await AchievementService(session).evaluate(db_user.id)
    await message.answer("✅ Трек добавлен", reply_markup=back_keyboard(f"plist:view:{pid}"))


@router.message(PlaylistStates.waiting_track)
async def st_track_text(message: Message, session: AsyncSession, db_user: User, state: FSMContext):
    data = await state.get_data()
    pid = data.get("track_playlist_id")
    text = (message.text or "").strip()
    parts = [x.strip() for x in text.split("|")]
    title = parts[0] if parts else "Track"
    performer = parts[1] if len(parts) > 1 else None
    url = parts[2] if len(parts) > 2 else text
    result = await PlaylistService(session).add_track(
        user_id=db_user.id,
        playlist_id=pid,
        file_id=url,
        file_unique_id=f"url:{db_user.id}:{pid}:{abs(hash(text))}",
        title=title,
        performer=performer,
        duration=None,
    )
    if result.get("error"):
        await message.answer(f"❌ {result['error']}")
        return
    await AchievementService(session).evaluate(db_user.id)
    await message.answer("✅ Трек/ссылка добавлены", reply_markup=back_keyboard(f"plist:view:{pid}"))


@router.callback_query(F.data.startswith("plist:play:"))
async def cb_play(callback: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    pid = int(callback.data.split(":")[2])
    playlist, tracks = await PlaylistService(session).get_playlist_tracks(db_user.id, pid)
    if not playlist:
        await callback.answer("Плейлист не найден")
        return
    sent_ids = []
    if not tracks:
        await callback.answer("Нет треков")
        return
    for t in tracks:
        try:
            sent = await callback.message.answer_audio(
                audio=t.file_id,
                caption=f"{playlist.emoji} {t.position}. {t.title or 'Track'}",
            )
            sent_ids.append(sent.message_id)
        except Exception:
            sent = await callback.message.answer(
                f"{playlist.emoji} {t.position}. {t.title or 'Track'}\n{t.file_id}"
            )
            sent_ids.append(sent.message_id)
    await state.update_data(**{f"playlist_sent_{pid}": sent_ids})
    await callback.message.answer(
        "▶️ Прослушивание запущено.\nНажми 'Выйти и удалить сообщения', чтобы очистить чат.",
        reply_markup=playlist_item_keyboard(pid),
    )
    await callback.answer("▶️")


@router.callback_query(F.data.startswith("plist:stop:"))
async def cb_stop(callback: CallbackQuery, state: FSMContext):
    pid = int(callback.data.split(":")[2])
    data = await state.get_data()
    sent_ids = data.get(f"playlist_sent_{pid}", [])
    for mid in sent_ids:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=mid)
        except Exception:
            pass
    await state.update_data(**{f"playlist_sent_{pid}": []})
    await callback.answer("🧹 Сообщения очищены")
    try:
        await callback.message.edit_text("🧹 Прослушивание остановлено", reply_markup=back_keyboard(f"plist:view:{pid}"))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("plist:del:"))
async def cb_delete(callback: CallbackQuery, session: AsyncSession, db_user: User):
    pid = int(callback.data.split(":")[2])
    result = await PlaylistService(session).delete_playlist(db_user.id, pid)
    if result.get("error"):
        await callback.answer(result["error"])
        return
    await callback.answer("Удалено")
    try:
        await callback.message.edit_text("🗑 Плейлист удален", reply_markup=playlists_menu_keyboard())
    except TelegramBadRequest:
        pass
