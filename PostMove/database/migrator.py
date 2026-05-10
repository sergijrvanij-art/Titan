from __future__ import annotations

from pathlib import Path

from PostMove.database.connection import Database


class Migrator:
    def __init__(self, db: Database, migrations_dir: Path) -> None:
        self._db = db
        self._dir = migrations_dir

    async def run(self) -> None:
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied_rows = await self._db.fetchall("SELECT name FROM schema_migrations")
        applied = {row["name"] for row in applied_rows}
        for migration in sorted(self._dir.glob("*.sql")):
            if migration.name in applied:
                continue
            await self._db.executescript(migration.read_text(encoding="utf-8"))
            await self._db.execute(
                "INSERT INTO schema_migrations(name) VALUES (?)",
                (migration.name,),
            )
