from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class LiveLogRecord:
    timestamp: str
    level: str
    event: str
    payload: dict


class LiveLogStream:
    def __init__(self, max_items: int = 2000) -> None:
        self._records: deque[LiveLogRecord] = deque(maxlen=max_items)
        self._subscribers: set[asyncio.Queue[LiveLogRecord]] = set()

    async def publish(self, level: str, event: str, payload: dict | None = None) -> None:
        record = LiveLogRecord(
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            level=level,
            event=event,
            payload=payload or {},
        )
        self._records.append(record)
        for queue in list(self._subscribers):
            await queue.put(record)

    def snapshot(self, limit: int = 100) -> list[dict]:
        items = list(self._records)[-limit:]
        return [asdict(item) for item in items]

    def subscribe(self) -> asyncio.Queue[LiveLogRecord]:
        queue: asyncio.Queue[LiveLogRecord] = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LiveLogRecord]) -> None:
        self._subscribers.discard(queue)
