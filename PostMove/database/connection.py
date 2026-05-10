from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        assert self._conn is not None
        async with self._lock:
            await self._conn.execute(sql, params)
            await self._conn.commit()

    async def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> None:
        assert self._conn is not None
        async with self._lock:
            await self._conn.executemany(sql, params)
            await self._conn.commit()

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict | None:
        assert self._conn is not None
        async with self._lock:
            cursor = await self._conn.execute(sql, params)
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict]:
        assert self._conn is not None
        async with self._lock:
            cursor = await self._conn.execute(sql, params)
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]
