from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from PostMove.bot.context import BotContext
from PostMove.bot.keyboards import logs_keyboard


def build_logs_router(ctx: BotContext) -> Router:
    router = Router(name="logs")

    @router.message(Command("logs"))
    async def logs_panel(message: Message) -> None:
        await message.answer("Logs controls", reply_markup=logs_keyboard())

    @router.callback_query(F.data == "logs:latest")
    async def logs_latest(callback: CallbackQuery) -> None:
        records = await ctx.logs_repo.list(limit=30)
        text = "\\n".join([f"[{row['level']}] {row['event']}" for row in records]) or "No logs"
        await callback.message.answer(text)
        await callback.answer()

    @router.callback_query(F.data == "logs:live")
    async def logs_live(callback: CallbackQuery) -> None:
        snapshot = ctx.live_logs.snapshot(limit=20)
        text = "\\n".join([f"[{item['level']}] {item['event']}" for item in snapshot]) or "No live logs"
        await callback.message.answer(text)
        await callback.answer()

    @router.callback_query(F.data == "logs:export")
    async def logs_export(callback: CallbackQuery) -> None:
        records = await ctx.logs_repo.list(limit=500)
        serialized = "\\n".join([str(row) for row in records]).encode("utf-8")
        file = BufferedInputFile(serialized, filename="postmove-logs.txt")
        await callback.message.answer_document(file)
        await callback.answer()

    @router.message(Command("logs_search"))
    async def logs_search(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Usage: /logs_search <query>")
            return
        records = await ctx.logs_repo.search(parts[1], limit=30)
        text = "\\n".join([f"[{row['level']}] {row['event']}" for row in records]) or "No matches"
        await message.answer(text)

    return router
