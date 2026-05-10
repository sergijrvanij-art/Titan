from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from PostMove.database.repositories import RuntimeRepository
from PostMove.parsers.engine import ParserEngine
from PostMove.queue.manager import JobQueue
from PostMove.telemetry.metrics import RuntimeMetrics


class HeartbeatService:
    def __init__(self, runtime_repo: RuntimeRepository, queue: JobQueue, parser_engine: ParserEngine) -> None:
        self._runtime_repo = runtime_repo
        self._queue = queue
        self._parser_engine = parser_engine
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="heartbeat")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            queue_state = await self._queue.snapshot()
            parser_state = await self._parser_engine.status()
            payload = {
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "runtime": RuntimeMetrics.snapshot(),
                "queue": queue_state,
                "parsers": parser_state,
            }
            await self._runtime_repo.heartbeat(payload)
            await asyncio.sleep(10)
