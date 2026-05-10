from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from PostMove.bot.context import BotContext
from PostMove.bot.keyboards import parser_keyboard


def build_parsers_router(ctx: BotContext) -> Router:
    router = Router(name="parsers")

    @router.message(Command("parsers"))
    async def parser_panel(message: Message) -> None:
        await message.answer("Parser controls", reply_markup=parser_keyboard())

    @router.callback_query(F.data == "parser:start")
    async def parser_start(callback: CallbackQuery) -> None:
        await ctx.parser_engine.resume()
        await callback.message.answer("Parsers resumed")
        await callback.answer()

    @router.callback_query(F.data == "parser:pause")
    async def parser_pause(callback: CallbackQuery) -> None:
        await ctx.parser_engine.pause()
        await callback.message.answer("Parsers paused")
        await callback.answer()

    @router.callback_query(F.data == "parser:restart")
    async def parser_restart(callback: CallbackQuery) -> None:
        await ctx.parser_engine.restart()
        await callback.message.answer("Parsers restarted")
        await callback.answer()

    @router.callback_query(F.data == "parser:stats")
    async def parser_stats(callback: CallbackQuery) -> None:
        status = await ctx.parser_engine.status()
        await callback.message.answer(str(status))
        await callback.answer()

    @router.callback_query(F.data == "parser:queue")
    async def parser_queue(callback: CallbackQuery) -> None:
        snapshot = await ctx.queue.snapshot()
        await callback.message.answer(f"Queue snapshot: {snapshot}")
        await callback.answer()

    return router
