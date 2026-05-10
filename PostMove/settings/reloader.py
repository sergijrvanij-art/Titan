from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

ReloadCallback = Callable[[], Awaitable[None]]


class ConfigReloader:
    def __init__(self, config_path: Path, interval: int = 15) -> None:
        self._config_path = config_path
        self._interval = interval
        self._callbacks: list[ReloadCallback] = []
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._last_mtime: float | None = None

    def subscribe(self, callback: ReloadCallback) -> None:
        self._callbacks.append(callback)

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        if self._config_path.exists():
            self._last_mtime = self._config_path.stat().st_mtime
        self._task = asyncio.create_task(self._run(), name="config-reloader")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(self._interval)
            if not self._config_path.exists():
                continue
            current = self._config_path.stat().st_mtime
            if self._last_mtime is None:
                self._last_mtime = current
                continue
            if current <= self._last_mtime:
                continue
            self._last_mtime = current
            for callback in self._callbacks:
                await callback()
