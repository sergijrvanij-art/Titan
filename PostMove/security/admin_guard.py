from __future__ import annotations


class AdminGuard:
    def __init__(self, admin_ids: set[int]) -> None:
        self._admin_ids = admin_ids

    def is_admin(self, user_id: int | None) -> bool:
        if user_id is None:
            return False
        return user_id in self._admin_ids
