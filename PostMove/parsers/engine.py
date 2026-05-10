from __future__ import annotations

import asyncio

from PostMove.database.repositories import CheckpointRepository, LogRepository, ParserStatsRepository
from PostMove.logging.structured import get_logger
from PostMove.parsers.base import Parser, ParserItem
from PostMove.parsers.news import NewsParser
from PostMove.queue.manager import JobQueue, QueueJob
from PostMove.settings.models import AppSettings

LOGGER = get_logger(__name__)


class ParserEngine:
    def __init__(
        self,
        settings: AppSettings,
        queue: JobQueue,
        parser_stats_repo: ParserStatsRepository,
        checkpoint_repo: CheckpointRepository,
        logs_repo: LogRepository,
    ) -> None:
        self._settings = settings
        self._queue = queue
        self._parser_stats_repo = parser_stats_repo
        self._checkpoint_repo = checkpoint_repo
        self._logs_repo = logs_repo
        self._parsers: list[Parser] = []
        self._userbot = None
        self._workers: list[asyncio.Task] = []
        self._paused = asyncio.Event()
        self._paused.set()
        self._stop_event = asyncio.Event()

    def reload_settings(self, settings: AppSettings) -> None:
        self._settings = settings

    async def start(self, userbot) -> None:
        self._stop_event.clear()
        self._paused.set()
        self._userbot = userbot
        if not self._parsers:
            self._parsers.append(NewsParser("news-parser", userbot))
        if self._workers:
            return
        for index in range(self._settings.core.parser_workers):
            task = asyncio.create_task(self._worker_loop(index), name=f"parser-worker-{index}")
            self._workers.append(task)

    async def stop(self) -> None:
        self._stop_event.set()
        self._paused.set()
        for worker in self._workers:
            worker.cancel()
        for worker in self._workers:
            try:
                await worker
            except asyncio.CancelledError:
                pass
        self._workers.clear()

    async def pause(self) -> None:
        self._paused.clear()

    async def resume(self) -> None:
        self._paused.set()

    async def restart(self) -> None:
        if self._userbot is None:
            return
        await self.stop()
        await self.start(self._userbot)

    async def status(self) -> dict:
        return {
            "parsers": [parser.name for parser in self._parsers],
            "workers": len(self._workers),
            "paused": not self._paused.is_set(),
            "stats": await self._parser_stats_repo.all(),
        }

    async def _worker_loop(self, worker_id: int) -> None:
        while not self._stop_event.is_set():
            await self._paused.wait()
            for parser in self._parsers:
                try:
                    items = await parser.parse()
                    await self._dispatch_items(items)
                    await self._parser_stats_repo.increment(parser.name, parsed=len(items))
                except Exception as exc:  # noqa: BLE001
                    await self._parser_stats_repo.increment(parser.name, errors=1)
                    await self._logs_repo.add("ERROR", "parser_failed", {"parser": parser.name, "error": str(exc)})
                    LOGGER.error("parser_failed", parser=parser.name, worker=worker_id, error=str(exc))
            await asyncio.sleep(3)

    async def _dispatch_items(self, items: list[ParserItem]) -> None:
        for item in items:
            payload = {
                "source_chat": item.source_chat,
                "target_chat": item.target_chat,
                "source_message_id": item.message_id,
                "text": item.text,
            }
            await self._queue.submit(QueueJob(job_type="transfer", payload=payload, priority=50))
