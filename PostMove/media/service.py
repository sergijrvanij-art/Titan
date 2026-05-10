from __future__ import annotations

import asyncio
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PostMove.logging.structured import get_logger
from PostMove.settings.models import MediaSettings

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class PreparedMedia:
    path: Path
    media_type: str
    cleanup_paths: list[Path]


class MediaService:
    def __init__(self, settings: MediaSettings) -> None:
        self._settings = settings
        self._temp_dir = Path(settings.temp_dir)
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    async def prepare_media(self, message) -> PreparedMedia | None:
        if not getattr(message, "media", None):
            return None

        media_type = self._detect_media_type(message)
        extension = self._detect_extension(message, media_type)
        output_path = self._temp_dir / f"{message.id}-{uuid4().hex}{extension}"
        downloaded = await message.download_media(file=str(output_path))
        if downloaded is None:
            return None

        base_path = Path(downloaded)
        cleanup_paths = [base_path]
        active_path = base_path

        if media_type == "photo" and self._settings.compress_photos:
            compressed = await self._compress_photo(base_path)
            if compressed != base_path:
                cleanup_paths.append(compressed)
                active_path = compressed
        elif media_type in {"video", "gif"} and self._settings.compress_videos:
            compressed = await self._compress_video(base_path)
            if compressed != base_path:
                cleanup_paths.append(compressed)
                active_path = compressed

        return PreparedMedia(path=active_path, media_type=media_type, cleanup_paths=cleanup_paths)

    async def cleanup(self, media: PreparedMedia | Path | None) -> None:
        if media is None or not self._settings.cleanup_temp:
            return
        paths: list[Path]
        if isinstance(media, PreparedMedia):
            paths = media.cleanup_paths
        else:
            paths = [media]
        unique_paths = {path for path in paths}
        for path in unique_paths:
            if path.exists():
                await asyncio.to_thread(path.unlink)

    def _detect_media_type(self, message) -> str:
        if getattr(message, "photo", None):
            return "photo"
        if getattr(message, "video", None):
            return "video"
        if getattr(message, "voice", None):
            return "voice"
        if getattr(message, "video_note", None):
            return "video_note"
        if getattr(message, "audio", None):
            return "audio"
        if getattr(message, "document", None):
            mime_type = getattr(getattr(message, "file", None), "mime_type", None)
            if mime_type == "image/gif":
                return "gif"
            return "document"
        return "unknown"

    def _detect_extension(self, message, media_type: str) -> str:
        file_obj = getattr(message, "file", None)
        ext = getattr(file_obj, "ext", None)
        if ext:
            return ext
        if media_type == "photo":
            return ".jpg"
        if media_type in {"video", "video_note"}:
            return ".mp4"
        if media_type == "voice":
            return ".ogg"
        guessed = mimetypes.guess_extension(getattr(file_obj, "mime_type", "") or "")
        return guessed or ".bin"

    async def _compress_photo(self, source: Path) -> Path:
        try:
            from PIL import Image
        except ImportError:
            LOGGER.warning("photo_compression_skipped_pillow_missing")
            return source

        target = source.with_name(f"{source.stem}-compressed.jpg")

        def _compress() -> None:
            with Image.open(source) as image:
                normalized = image.convert("RGB")
                normalized.thumbnail((1920, 1920))
                normalized.save(target, format="JPEG", quality=82, optimize=True, progressive=True)

        await asyncio.to_thread(_compress)
        return target

    async def _compress_video(self, source: Path) -> Path:
        target = source.with_name(f"{source.stem}-compressed.mp4")
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vcodec",
            "libx264",
            "-crf",
            "28",
            "-preset",
            "veryfast",
            "-acodec",
            "aac",
            "-movflags",
            "+faststart",
            str(target),
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
        except FileNotFoundError:
            LOGGER.warning("video_compression_skipped_ffmpeg_missing")
            return source

        if process.returncode != 0:
            LOGGER.warning("video_compression_failed", error=stderr.decode("utf-8", errors="ignore"))
            if target.exists():
                await asyncio.to_thread(target.unlink)
            return source
        return target
