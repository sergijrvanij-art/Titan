from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from PostMove.bot.context import BotContext


def build_runtime_router(ctx: BotContext) -> Router:
    router = Router(name="runtime")

    @router.message(Command("runtime"))
    async def runtime(message: Message) -> None:
        state = await ctx.runtime_repo.get_heartbeat()
        parser_status = await ctx.parser_engine.status()
        queue_status = await ctx.queue.snapshot()
        await message.answer(f"Heartbeat: {state}\nParsers: {parser_status}\nQueue: {queue_status}")

    return router
