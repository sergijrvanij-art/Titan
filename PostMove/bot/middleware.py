from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from PostMove.security.admin_guard import AdminGuard


class AdminOnlyMiddleware(BaseMiddleware):
    def __init__(self, admin_guard: AdminGuard) -> None:
        super().__init__()
        self._guard = admin_guard

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        user_id = getattr(from_user, "id", None)
        if not self._guard.is_admin(user_id):
            message = getattr(event, "message", None)
            if message:
                await message.answer("Access denied")
            return None
        return await handler(event, data)
