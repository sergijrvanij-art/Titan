from __future__ import annotations

import asyncio
import time


class AsyncRateLimiter:
    def __init__(self, rate_per_sec: float) -> None:
        self._rate_per_sec = max(rate_per_sec, 0.1)
        self._lock = asyncio.Lock()
        self._next_allowed = time.monotonic()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            self._next_allowed = now + (1 / self._rate_per_sec)
