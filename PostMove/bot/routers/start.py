from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from PostMove.bot.keyboards import main_menu_keyboard


def build_start_router() -> Router:
    router = Router(name="start")

    @router.message(Command("start"))
    async def on_start(message: Message) -> None:
        await message.answer("PostMove admin panel", reply_markup=main_menu_keyboard())

    return router
