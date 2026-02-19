from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.playlist_repo import PlaylistRepository
from src.services.gamification_service import GamificationService


class PlaylistService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PlaylistRepository(session)
        self.gamification = GamificationService(session)

    async def create_playlist(
        self,
        user_id: int,
        name: str,
        emoji: str = "🎵",
    ) -> dict:
        playlist = await self.repo.create(
            user_id=user_id,
            name=name,
            emoji=emoji,
        )
        await self.gamification.award_xp(
            user_id,
            event_type="playlist_created",
            xp_amount=10,
            source_type="playlist",
            source_id=playlist.id,
        )
        return {"playlist_id": playlist.id, "name": playlist.name, "emoji": playlist.emoji}

    async def add_track(
        self,
        user_id: int,
        playlist_id: int,
        file_id: str,
        file_unique_id: str,
        title: str | None = None,
        performer: str | None = None,
        duration: int | None = None,
    ) -> dict:
        playlist = await self.repo.get_by_id(playlist_id)
        if not playlist:
            return {"error": "Плейлист не найден"}
        if playlist.user_id != user_id:
            return {"error": "Это не твой плейлист"}

        track = await self.repo.add_track(
            playlist_id=playlist_id,
            file_id=file_id,
            file_unique_id=file_unique_id,
            title=title,
            performer=performer,
            duration=duration,
        )
        await self.gamification.award_xp(
            user_id,
            event_type="playlist_track_added",
            xp_amount=4,
            source_type="playlist_track",
            source_id=track.id,
        )
        return {
            "track_id": track.id,
            "title": track.title,
            "performer": track.performer,
            "position": track.position,
        }

    async def delete_playlist(self, user_id: int, playlist_id: int) -> dict:
        playlist = await self.repo.get_by_id(playlist_id)
        if not playlist:
            return {"error": "Плейлист не найден"}
        if playlist.user_id != user_id:
            return {"error": "Это не твой плейлист"}
        await self.repo.delete(playlist_id)
        return {"deleted": True, "name": playlist.name}

    async def get_user_playlists(self, user_id: int):
        return await self.repo.get_user_playlists(user_id)

    async def get_playlist_tracks(self, user_id: int, playlist_id: int):
        playlist = await self.repo.get_by_id(playlist_id)
        if not playlist or playlist.user_id != user_id:
            return None, []
        tracks = await self.repo.get_playlist_tracks(playlist_id)
        return playlist, tracks
