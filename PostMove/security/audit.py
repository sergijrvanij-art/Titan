from __future__ import annotations

from PostMove.database.repositories import AdminActionRepository, LogRepository


class AuditService:
    def __init__(self, actions_repo: AdminActionRepository, logs_repo: LogRepository) -> None:
        self._actions_repo = actions_repo
        self._logs_repo = logs_repo

    async def record(self, admin_id: int, action: str, payload: dict | None = None) -> None:
        await self._actions_repo.add(admin_id, action, payload)
        await self._logs_repo.add("INFO", "admin_action", {"admin_id": admin_id, "action": action, "payload": payload or {}})
