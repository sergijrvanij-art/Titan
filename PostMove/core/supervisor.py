from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from PostMove.logging.structured import get_logger

LOGGER = get_logger(__name__)


class ModuleSupervisor:
    def __init__(self) -> None:
        self._modules: dict[str, Callable[[], Awaitable[None]]] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._stop_event = asyncio.Event()

    async def start_module(self, name: str, runner: Callable[[], Awaitable[None]]) -> None:
        self._modules[name] = runner
        if name not in self._tasks or self._tasks[name].done():
            self._tasks[name] = asyncio.create_task(runner(), name=f"module-{name}")

    async def watch(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(2)
            for name, task in list(self._tasks.items()):
                if not task.done():
                    continue
                exc = task.exception()
                if exc:
                    LOGGER.error("module_crashed", module=name, error=str(exc))
                runner = self._modules.get(name)
                if runner and not self._stop_event.is_set():
                    LOGGER.warning("module_restarting", module=name)
                    self._tasks[name] = asyncio.create_task(runner(), name=f"module-{name}")

    async def stop_all(self) -> None:
        self._stop_event.set()
        for task in self._tasks.values():
            task.cancel()
        for task in self._tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
