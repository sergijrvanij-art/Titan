from __future__ import annotations

import json
from typing import Any

from PostMove.database.connection import Database


class ChannelRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add(self, source: str, target: str, enabled: bool = True) -> None:
        await self._db.execute(
            """
            INSERT INTO channels(source_channel, target_channel, enabled)
            VALUES (?, ?, ?)
            """,
            (source, target, int(enabled)),
        )

    async def update(self, channel_id: int, source: str, target: str, enabled: bool) -> None:
        await self._db.execute(
            """
            UPDATE channels
            SET source_channel=?, target_channel=?, enabled=?
            WHERE id=?
            """,
            (source, target, int(enabled), channel_id),
        )

    async def remove(self, channel_id: int) -> None:
        await self._db.execute("DELETE FROM channels WHERE id=?", (channel_id,))

    async def list(self, only_enabled: bool = False) -> list[dict]:
        if only_enabled:
            return await self._db.fetchall("SELECT * FROM channels WHERE enabled=1 ORDER BY id")
        return await self._db.fetchall("SELECT * FROM channels ORDER BY id")


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def set(self, key: str, value: Any) -> None:
        await self._db.execute(
            """
            INSERT INTO parser_settings(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, json.dumps(value)),
        )

    async def get(self, key: str, default: Any = None) -> Any:
        row = await self._db.fetchone("SELECT value FROM parser_settings WHERE key=?", (key,))
        if not row:
            return default
        return json.loads(row["value"])


class TransferJobRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, kind: str, payload: dict, status: str = "queued") -> int:
        await self._db.execute(
            "INSERT INTO transfer_jobs(kind, payload, status) VALUES (?, ?, ?)",
            (kind, json.dumps(payload), status),
        )
        row = await self._db.fetchone("SELECT last_insert_rowid() as id")
        return int(row["id"])

    async def set_status(self, job_id: int, status: str, error: str | None = None) -> None:
        await self._db.execute(
            "UPDATE transfer_jobs SET status=?, error=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, error, job_id),
        )

    async def list_active(self) -> list[dict]:
        return await self._db.fetchall(
            "SELECT * FROM transfer_jobs WHERE status IN ('queued', 'running') ORDER BY id"
        )


class PostRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def exists(self, source_chat: str, source_message_id: int) -> bool:
        row = await self._db.fetchone(
            "SELECT 1 FROM posts WHERE source_chat=? AND source_message_id=?",
            (source_chat, source_message_id),
        )
        return row is not None

    async def save_mapping(
        self,
        source_chat: str,
        source_message_id: int,
        target_chat: str,
        target_message_id: int,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO posts(source_chat, source_message_id, target_chat, target_message_id)
            VALUES (?, ?, ?, ?)
            """,
            (source_chat, source_message_id, target_chat, target_message_id),
        )


class LogRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add(self, level: str, event: str, payload: dict | None = None) -> None:
        await self._db.execute(
            "INSERT INTO logs(level, event, payload) VALUES (?, ?, ?)",
            (level, event, json.dumps(payload or {})),
        )

    async def list(self, level: str | None = None, limit: int = 200) -> list[dict]:
        if level:
            return await self._db.fetchall(
                "SELECT * FROM logs WHERE level=? ORDER BY id DESC LIMIT ?",
                (level, limit),
            )
        return await self._db.fetchall("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))

    async def search(self, query: str, limit: int = 200) -> list[dict]:
        pattern = f"%{query}%"
        return await self._db.fetchall(
            "SELECT * FROM logs WHERE event LIKE ? OR payload LIKE ? ORDER BY id DESC LIMIT ?",
            (pattern, pattern, limit),
        )


class RuntimeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def heartbeat(self, payload: dict) -> None:
        await self._db.execute(
            """
            INSERT INTO runtime_state(key, value)
            VALUES ('heartbeat', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """,
            (json.dumps(payload),),
        )

    async def get_heartbeat(self) -> dict | None:
        row = await self._db.fetchone("SELECT value FROM runtime_state WHERE key='heartbeat'")
        if not row:
            return None
        return json.loads(row["value"])


class CheckpointRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def set(self, name: str, value: dict) -> None:
        await self._db.execute(
            """
            INSERT INTO checkpoints(name, value)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """,
            (name, json.dumps(value)),
        )

    async def get(self, name: str) -> dict | None:
        row = await self._db.fetchone("SELECT value FROM checkpoints WHERE name=?", (name,))
        if not row:
            return None
        return json.loads(row["value"])


class ParserStatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def increment(self, parser_name: str, parsed: int = 0, errors: int = 0) -> None:
        row = await self._db.fetchone(
            "SELECT parsed_count, error_count FROM parser_stats WHERE parser_name=?",
            (parser_name,),
        )
        if not row:
            await self._db.execute(
                "INSERT INTO parser_stats(parser_name, parsed_count, error_count) VALUES (?, ?, ?)",
                (parser_name, parsed, errors),
            )
            return
        await self._db.execute(
            """
            UPDATE parser_stats
            SET parsed_count=?, error_count=?, updated_at=CURRENT_TIMESTAMP
            WHERE parser_name=?
            """,
            (row["parsed_count"] + parsed, row["error_count"] + errors, parser_name),
        )

    async def all(self) -> list[dict]:
        return await self._db.fetchall("SELECT * FROM parser_stats ORDER BY parser_name")


class AdminActionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add(self, admin_id: int, action: str, payload: dict | None = None) -> None:
        await self._db.execute(
            "INSERT INTO admin_actions(admin_id, action, payload) VALUES (?, ?, ?)",
            (admin_id, action, json.dumps(payload or {})),
        )
