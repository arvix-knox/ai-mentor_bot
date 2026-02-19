from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.playlist import Playlist, PlaylistTrack
from src.repositories.base import BaseRepository


class PlaylistRepository(BaseRepository):
    model = Playlist

    async def get_user_playlists(self, user_id: int) -> list[Playlist]:
        stmt = (
            select(Playlist)
            .where(Playlist.user_id == user_id)
            .order_by(Playlist.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_playlist_tracks(self, playlist_id: int) -> list[PlaylistTrack]:
        stmt = (
            select(PlaylistTrack)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_track(
        self,
        playlist_id: int,
        file_id: str,
        file_unique_id: str,
        title: str | None = None,
        performer: str | None = None,
        duration: int | None = None,
    ) -> PlaylistTrack:
        count_stmt = select(func.count()).where(PlaylistTrack.playlist_id == playlist_id)
        count_result = await self.session.execute(count_stmt)
        position = int(count_result.scalar() or 0) + 1

        track = PlaylistTrack(
            playlist_id=playlist_id,
            file_id=file_id,
            file_unique_id=file_unique_id,
            title=title,
            performer=performer,
            duration=duration,
            position=position,
        )
        self.session.add(track)
        await self.session.flush()
        await self.session.refresh(track)
        return track

    async def delete_playlist_tracks(self, playlist_id: int) -> int:
        tracks = await self.get_playlist_tracks(playlist_id)
        for t in tracks:
            await self.session.delete(t)
        await self.session.flush()
        return len(tracks)
