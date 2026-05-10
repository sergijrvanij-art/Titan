from __future__ import annotations

import asyncio
import time

from telethon.utils import get_display_name

from PostMove.ai.modules import AIModuleService
from PostMove.database.repositories import (
    ChannelRepository,
    CheckpointRepository,
    LogRepository,
    PostRepository,
    SettingsRepository,
    TransferJobRepository,
)
from PostMove.logging.structured import get_logger
from PostMove.media.service import MediaService
from PostMove.processing.pipeline import ContentProcessor
from PostMove.queue.manager import JobQueue, QueueJob
from PostMove.settings.models import AppSettings

LOGGER = get_logger(__name__)


class TransferService:
    def __init__(
        self,
        settings: AppSettings,
        userbot,
        queue: JobQueue,
        channels_repo: ChannelRepository,
        transfer_repo: TransferJobRepository,
        posts_repo: PostRepository,
        checkpoint_repo: CheckpointRepository,
        content_processor: ContentProcessor,
        media_service: MediaService,
        logs_repo: LogRepository,
        settings_repo: SettingsRepository,
        ai_service: AIModuleService | None = None,
    ) -> None:
        self._settings = settings
        self._userbot = userbot
        self._queue = queue
        self._channels_repo = channels_repo
        self._transfer_repo = transfer_repo
        self._posts_repo = posts_repo
        self._checkpoint_repo = checkpoint_repo
        self._content_processor = content_processor
        self._media_service = media_service
        self._logs_repo = logs_repo
        self._settings_repo = settings_repo
        self._ai = ai_service or AIModuleService()
        self._paused = asyncio.Event()
        self._paused.set()
        self._cancelled = False
        self._listener_registered = False
        self._live_enabled = settings.transfer.live_mode_enabled
        self._completed = 0
        self._failed = 0
        self._last_activity: str | None = None
        self._runtime_reactions = list(settings.transfer.reaction_emojis)
        self._runtime_delay = settings.transfer.transfer_delay_seconds
        self._runtime_cache_ts = 0.0
        self._runtime_cache_ttl = 5.0
        self._userbot.set_channel_provider(channels_repo)

    def reload_settings(self, settings: AppSettings) -> None:
        self._settings = settings
        self._content_processor.reload(settings.processing)
        self._runtime_reactions = list(settings.transfer.reaction_emojis)
        self._runtime_delay = settings.transfer.transfer_delay_seconds

    async def start_history_transfer(self, source: str, target: str, limit: int = 500) -> int:
        payload = {"source": source, "target": target, "limit": limit}
        job_id = await self._transfer_repo.create("history", payload)
        await self._logs_repo.add("INFO", "transfer_history_start", payload)

        checkpoint = await self._checkpoint_repo.get(f"history:{source}:{target}")
        min_id = checkpoint["last_message_id"] if checkpoint else 0

        async for message in self._userbot.iter_messages(source, limit=limit):
            if message.id <= min_id:
                continue
            await self._queue.submit(
                QueueJob(
                    job_type="transfer",
                    payload={
                        "source_chat": source,
                        "target_chat": target,
                        "source_message_id": message.id,
                        "text": getattr(message, "message", "") or "",
                    },
                    priority=100,
                )
            )
        return job_id

    async def enable_live_transfer(self) -> None:
        if self._listener_registered:
            return

        async def callback(event) -> None:
            if not self._live_enabled:
                return
            source = get_display_name(event.chat) if event.chat else str(event.chat_id)
            records = await self._channels_repo.list(only_enabled=True)
            target = next((row["target_channel"] for row in records if row["source_channel"] == source), None)
            if not target:
                return
            await self._queue.submit(
                QueueJob(
                    job_type="transfer",
                    payload={
                        "source_chat": source,
                        "target_chat": target,
                        "source_message_id": event.message.id,
                        "text": event.message.message or "",
                    },
                    priority=10,
                )
            )

        await self._userbot.register_live_listener(callback)
        self._listener_registered = True

    async def toggle_live_mode(self) -> bool:
        self._live_enabled = not self._live_enabled
        await self._logs_repo.add("INFO", "transfer_live_mode_changed", {"enabled": self._live_enabled})
        return self._live_enabled

    async def pause(self) -> None:
        self._paused.clear()

    async def resume(self) -> None:
        self._paused.set()

    async def cancel(self) -> None:
        self._cancelled = True
        await self._logs_repo.add("WARNING", "transfer_cancelled", {})

    async def progress(self) -> dict:
        queue_snapshot = await self._queue.snapshot()
        active_jobs = await self._transfer_repo.list_active()
        return {
            "live_enabled": self._live_enabled,
            "paused": not self._paused.is_set(),
            "cancelled": self._cancelled,
            "completed": self._completed,
            "failed": self._failed,
            "last_activity": self._last_activity,
            "active_jobs": active_jobs,
            "queue": queue_snapshot,
        }

    async def handle_queue_job(self, job: QueueJob) -> None:
        await self._paused.wait()
        if self._cancelled:
            await self._logs_repo.add("WARNING", "transfer_cancelled_drop_job", job.payload)
            return

        try:
            source_chat = str(job.payload["source_chat"])
            source_message_id = int(job.payload["source_message_id"])
            target_chat = str(job.payload["target_chat"])

            if await self._posts_repo.exists(source_chat, source_message_id):
                await self._logs_repo.add("INFO", "transfer_duplicate_skipped", job.payload)
                return

            source_message = await self._userbot.get_message(source_chat, source_message_id)
            processed = self._content_processor.process(job.payload.get("text"))
            if processed.denied:
                await self._logs_repo.add("INFO", "transfer_denied", {"message_id": source_message_id})
                return
            await self._refresh_runtime_overrides()
            ai_result = self._ai.analyze(processed.text)
            if (
                self._settings.ai.enabled
                and (
                    ai_result.moderation_score >= self._settings.ai.moderation_threshold
                    or ai_result.fake_score >= self._settings.ai.fake_detection_threshold
                )
            ):
                await self._logs_repo.add(
                    "WARNING",
                    "transfer_ai_blocked",
                    {
                        "message_id": source_message_id,
                        "moderation_score": ai_result.moderation_score,
                        "fake_score": ai_result.fake_score,
                    },
                )
                return
            await self._logs_repo.add(
                "INFO",
                "transfer_ai_scored",
                {
                    "message_id": source_message_id,
                    "trust_score": ai_result.trust_score,
                    "sentiment": ai_result.sentiment,
                    "category": ai_result.category,
                    "generated_title": ai_result.title,
                    "summary": ai_result.summary,
                },
            )

            prepared_media = await self._media_service.prepare_media(source_message)
            try:
                if prepared_media:
                    sent = await self._userbot.send_media(
                        target_chat,
                        prepared_media.path,
                        caption=processed.text,
                        buttons=processed.buttons or None,
                    )
                else:
                    sent = await self._userbot.send_text(
                        target_chat,
                        processed.text,
                        buttons=processed.buttons or None,
                    )
            finally:
                await self._media_service.cleanup(prepared_media)

            await self._posts_repo.save_mapping(source_chat, source_message_id, target_chat, sent.id)
            await self._checkpoint_repo.set(
                f"history:{source_chat}:{target_chat}",
                {"last_message_id": source_message_id},
            )
            reacted = await self._userbot.react_to_discussion_comments(
                channel=target_chat,
                channel_message_id=sent.id,
                emojis=self._runtime_reactions,
                comments_limit=self._settings.transfer.discussion_comment_scan_limit,
            )
            if reacted:
                await self._logs_repo.add(
                    "INFO",
                    "discussion_comment_reacted",
                    {"target_chat": target_chat, "message_id": sent.id, "count": reacted},
                )
            if self._runtime_delay > 0:
                await asyncio.sleep(self._runtime_delay)
            await self._logs_repo.add(
                "INFO",
                "transfer_done",
                {"source": source_chat, "target": target_chat, "source_id": source_message_id},
            )
            self._completed += 1
            self._last_activity = f"{source_chat}:{source_message_id}"
        except Exception:
            self._failed += 1
            raise

    async def _refresh_runtime_overrides(self) -> None:
        now = time.monotonic()
        if now - self._runtime_cache_ts < self._runtime_cache_ttl:
            return
        self._runtime_cache_ts = now

        reactions = await self._settings_repo.get("reactions", default=None)
        if isinstance(reactions, list):
            normalized = [str(item).strip() for item in reactions if str(item).strip()]
            if normalized:
                self._runtime_reactions = normalized

        delays = await self._settings_repo.get("delays", default=None)
        if isinstance(delays, dict):
            raw_delay = delays.get("transfer_delay_seconds")
            if isinstance(raw_delay, (int, float)) and raw_delay >= 0:
                self._runtime_delay = float(raw_delay)
