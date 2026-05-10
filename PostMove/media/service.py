from __future__ import annotations

import asyncio
from pathlib import Path

from PostMove.settings.models import MediaSettings


class MediaService:
    def __init__(self, settings: MediaSettings) -> None:
        self._settings = settings
        self._temp_dir = Path(settings.temp_dir)
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    async def prepare_media(self, message) -> Path | None:
        if not getattr(message, "media", None):
            return None
        output_path = self._temp_dir / f"{message.id}"
        await message.download_media(file=str(output_path))
        return output_path

    async def cleanup(self, path: Path | None) -> None:
        if not path or not self._settings.cleanup_temp:
            return
        if path.exists():
            await asyncio.to_thread(path.unlink)
