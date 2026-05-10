from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from PostMove.parsers.news import NewsParser
from PostMove.processing.pipeline import ContentProcessor
from PostMove.queue.manager import JobQueue, QueueJob
from PostMove.settings.models import AppSettings, ProcessingSettings, QueueSettings
from PostMove.transfer.service import TransferService


class FakeLogsRepo:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict]] = []

    async def add(self, level: str, event: str, payload: dict | None = None) -> None:
        self.records.append((level, event, payload or {}))


class FakeLiveLogs:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict]] = []

    async def publish(self, level: str, event: str, payload: dict | None = None) -> None:
        self.records.append((level, event, payload or {}))


class QueueIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_jobs_move_to_dead_letter_after_retries(self) -> None:
        logs = FakeLogsRepo()
        live_logs = FakeLiveLogs()
        settings = QueueSettings(
            max_size=100,
            default_retries=1,
            worker_concurrency=1,
            base_backoff_seconds=0,
            max_backoff_seconds=0,
            rate_limit_per_second=100,
        )
        queue = JobQueue(settings, logs, live_logs)

        async def failing_handler(job: QueueJob) -> None:
            raise RuntimeError("boom")

        queue.register_handler("transfer", failing_handler)
        await queue.start()
        await queue.submit(QueueJob(job_type="transfer", payload={"x": 1}, max_retries=1))

        async def _wait_for_dead_letter() -> None:
            for _ in range(200):
                snapshot = await queue.snapshot()
                if snapshot["dead_letter"] == 1:
                    return
                await asyncio.sleep(0.01)
            raise AssertionError("dead letter queue did not receive failed job")

        try:
            await _wait_for_dead_letter()
            snapshot = await queue.snapshot()
            self.assertEqual(snapshot["dead_letter"], 1)
        finally:
            await queue.stop()


@dataclass(slots=True)
class DummyMessage:
    id: int
    message: str
    media: object | None = None


@dataclass(slots=True)
class DummySentMessage:
    id: int


class FakeUserbot:
    def __init__(self) -> None:
        self.sent_text: list[tuple[str, str]] = []
        self.reaction_calls: list[dict] = []

    def set_channel_provider(self, provider) -> None:
        self.channel_provider = provider

    async def get_message(self, chat: str, message_id: int):
        return DummyMessage(id=message_id, message="Hello world")

    async def send_text(self, target_chat: str, text: str, buttons=None):
        self.sent_text.append((target_chat, text))
        return DummySentMessage(id=9001)

    async def send_media(self, target_chat: str, file_path, caption: str | None = None, buttons=None):
        raise AssertionError("media path is not expected in this test")

    async def react_to_discussion_comments(self, channel: str, channel_message_id: int, emojis: list[str], comments_limit: int = 20) -> int:
        self.reaction_calls.append(
            {
                "channel": channel,
                "message_id": channel_message_id,
                "emojis": emojis,
                "comments_limit": comments_limit,
            }
        )
        return 2


class FakeQueue:
    async def snapshot(self) -> dict[str, int]:
        return {"queue_size": 0, "dead_letter": 0, "workers": 0}


class FakeChannelsRepo:
    async def list(self, only_enabled: bool = False) -> list[dict]:
        return []


class FakeTransferJobsRepo:
    async def create(self, kind: str, payload: dict, status: str = "queued") -> int:
        return 1

    async def list_active(self) -> list[dict]:
        return []


class FakePostsRepo:
    def __init__(self) -> None:
        self.saved: list[tuple[str, int, str, int]] = []

    async def exists(self, source_chat: str, source_message_id: int) -> bool:
        return False

    async def save_mapping(self, source_chat: str, source_message_id: int, target_chat: str, target_message_id: int) -> None:
        self.saved.append((source_chat, source_message_id, target_chat, target_message_id))


class FakeCheckpointRepo:
    async def get(self, name: str) -> dict | None:
        return None

    async def set(self, name: str, value: dict) -> None:
        self.last = (name, value)


class FakeMediaService:
    async def prepare_media(self, message):
        return None

    async def cleanup(self, media) -> None:
        return None


class FakeSettingsRepo:
    def __init__(self) -> None:
        self._values = {
            "reactions": ["👍", "🔥"],
            "delays": {"transfer_delay_seconds": 0},
        }

    async def get(self, key: str, default=None):
        return self._values.get(key, default)


class TransferIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_transfer_adds_mapping_and_reacts_to_discussion(self) -> None:
        settings = AppSettings.from_dict(
            {
                "core": {
                    "parser_workers": 1,
                    "queue_workers": 1,
                    "config_reload_interval": 10,
                    "graceful_shutdown_timeout": 10,
                },
                "telegram": {
                    "api_id": 1,
                    "api_hash": "hash",
                    "session_name": "session",
                    "admin_bot_token": "token",
                    "request_timeout": 30,
                    "flood_sleep_threshold": 10,
                },
                "database": {"path": "test.db"},
                "security": {"admin_ids": [1], "allow_forwarding_to_unlisted": False},
                "queue": {
                    "max_size": 100,
                    "default_retries": 1,
                    "worker_concurrency": 1,
                    "base_backoff_seconds": 0,
                    "max_backoff_seconds": 1,
                    "rate_limit_per_second": 100,
                },
                "processing": {
                    "source_markers": [],
                    "replacers": {},
                    "deny_words": [],
                    "auto_bold_title": False,
                    "default_buttons": [],
                },
                "media": {
                    "temp_dir": "./tmp_test_media",
                    "compress_photos": False,
                    "compress_videos": False,
                    "cleanup_temp": True,
                },
                "transfer": {
                    "live_mode_enabled": True,
                    "transfer_delay_seconds": 0,
                    "reaction_emojis": ["👍"],
                    "discussion_comment_scan_limit": 10,
                },
                "logging": {"level": "INFO", "json": False, "live_buffer": 10},
                "ai": {
                    "enabled": True,
                    "moderation_threshold": 0.95,
                    "fake_detection_threshold": 0.95,
                },
            }
        )

        userbot = FakeUserbot()
        posts_repo = FakePostsRepo()
        transfer = TransferService(
            settings=settings,
            userbot=userbot,
            queue=FakeQueue(),
            channels_repo=FakeChannelsRepo(),
            transfer_repo=FakeTransferJobsRepo(),
            posts_repo=posts_repo,
            checkpoint_repo=FakeCheckpointRepo(),
            content_processor=ContentProcessor(ProcessingSettings()),
            media_service=FakeMediaService(),
            logs_repo=FakeLogsRepo(),
            settings_repo=FakeSettingsRepo(),
        )

        job = QueueJob(
            job_type="transfer",
            payload={
                "source_chat": "source",
                "target_chat": "target",
                "source_message_id": 123,
                "text": "Hello world",
            },
            priority=10,
        )

        await transfer.handle_queue_job(job)

        self.assertEqual(len(posts_repo.saved), 1)
        self.assertEqual(posts_repo.saved[0], ("source", 123, "target", 9001))
        self.assertEqual(len(userbot.sent_text), 1)
        self.assertEqual(len(userbot.reaction_calls), 1)
        self.assertEqual(userbot.reaction_calls[0]["emojis"], ["👍", "🔥"])


@dataclass(slots=True)
class ParserMsg:
    id: int
    message: str


class FakeParserUserbot:
    def __init__(self) -> None:
        self.calls = 0

    async def channel_mappings(self) -> list[tuple[str, str]]:
        return [("source-channel", "target-channel")]

    async def iter_messages(self, source: str, limit: int = 25):
        self.calls += 1
        for item in [ParserMsg(5, "A"), ParserMsg(4, "B")]:
            yield item


class ParserIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_news_parser_uses_internal_checkpoint_cache(self) -> None:
        parser = NewsParser("news", FakeParserUserbot())
        first = await parser.parse()
        second = await parser.parse()

        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 0)


if __name__ == "__main__":
    unittest.main()
