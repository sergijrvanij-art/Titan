from __future__ import annotations

import asyncio
import itertools
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from PostMove.database.repositories import LogRepository
from PostMove.logging.live_stream import LiveLogStream
from PostMove.logging.structured import get_logger
from PostMove.queue.rate_limiter import AsyncRateLimiter
from PostMove.settings.models import QueueSettings

LOGGER = get_logger(__name__)


@dataclass(slots=True)
class QueueJob:
    job_type: str
    payload: dict[str, Any]
    priority: int = 100
    attempts: int = 0
    max_retries: int = 5
    created_monotonic: float = field(default_factory=monotonic)


Handler = Callable[[QueueJob], Awaitable[None]]


class JobQueue:
    def __init__(self, settings: QueueSettings, logs_repo: LogRepository, live_logs: LiveLogStream) -> None:
        self._settings = settings
        self._logs_repo = logs_repo
        self._live_logs = live_logs
        self._queue: asyncio.PriorityQueue[tuple[int, int, QueueJob]] = asyncio.PriorityQueue(maxsize=settings.max_size)
        self._dead_letter: list[QueueJob] = []
        self._handlers: dict[str, Handler] = {}
        self._workers: list[asyncio.Task] = []
        self._counter = itertools.count()
        self._stop_event = asyncio.Event()
        self._rate_limiter = AsyncRateLimiter(settings.rate_limit_per_second)

    def register_handler(self, job_type: str, handler: Handler) -> None:
        self._handlers[job_type] = handler

    async def start(self) -> None:
        self._stop_event.clear()
        if self._workers:
            return
        for idx in range(self._settings.worker_concurrency):
            task = asyncio.create_task(self._worker_loop(idx), name=f"queue-worker-{idx}")
            self._workers.append(task)

    async def stop(self) -> None:
        self._stop_event.set()
        for _ in self._workers:
            await self._queue.put((10**9, next(self._counter), QueueJob(job_type="__stop__", payload={})))
        for task in self._workers:
            await task
        self._workers.clear()

    async def submit(self, job: QueueJob) -> None:
        if job.max_retries <= 0:
            job.max_retries = self._settings.default_retries
        await self._queue.put((job.priority, next(self._counter), job))
        await self._record("INFO", "queue_job_submitted", {"type": job.job_type, "priority": job.priority})

    async def snapshot(self) -> dict[str, int]:
        return {
            "queue_size": self._queue.qsize(),
            "dead_letter": len(self._dead_letter),
            "workers": len(self._workers),
        }

    async def _worker_loop(self, worker_id: int) -> None:
        while not self._stop_event.is_set():
            _, _, job = await self._queue.get()
            if job.job_type == "__stop__":
                self._queue.task_done()
                break
            await self._rate_limiter.acquire()
            handler = self._handlers.get(job.job_type)
            if not handler:
                await self._record("ERROR", "queue_unknown_job_type", {"type": job.job_type})
                self._queue.task_done()
                continue
            try:
                await handler(job)
            except Exception as exc:  # noqa: BLE001
                await self._handle_retry(job, exc)
            else:
                await self._record("INFO", "queue_job_done", {"type": job.job_type, "worker": worker_id})
            finally:
                self._queue.task_done()

    async def _handle_retry(self, job: QueueJob, exc: Exception) -> None:
        job.attempts += 1
        payload = {
            "type": job.job_type,
            "attempt": job.attempts,
            "max_retries": job.max_retries,
            "error": str(exc),
        }
        if job.attempts > job.max_retries:
            self._dead_letter.append(job)
            await self._record("ERROR", "queue_job_dead_letter", payload)
            return
        backoff = min(
            self._settings.base_backoff_seconds * (2 ** (job.attempts - 1)),
            self._settings.max_backoff_seconds,
        )
        await self._record("WARNING", "queue_job_retry", {**payload, "backoff": backoff})
        await asyncio.sleep(backoff)
        await self.submit(job)

    async def _record(self, level: str, event: str, payload: dict[str, Any]) -> None:
        log_method = getattr(LOGGER, level.lower(), LOGGER.info)
        log_method(event, **payload)
        await self._logs_repo.add(level, event, payload)
        await self._live_logs.publish(level, event, payload)
