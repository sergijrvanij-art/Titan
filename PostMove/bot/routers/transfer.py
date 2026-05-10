from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from PostMove.bot.context import BotContext
from PostMove.bot.keyboards import transfer_keyboard


def build_transfer_router(ctx: BotContext) -> Router:
    router = Router(name="transfer")

    @router.message(Command("transfer"))
    async def transfer_panel(message: Message) -> None:
        await message.answer("Transfer controls", reply_markup=transfer_keyboard())

    @router.callback_query(F.data == "transfer:start")
    async def transfer_start(callback: CallbackQuery) -> None:
        channels = await ctx.channels_repo.list(only_enabled=True)
        for item in channels:
            await ctx.transfer_service.start_history_transfer(item["source_channel"], item["target_channel"], limit=300)
        await callback.message.answer("History transfer jobs queued")
        await callback.answer()

    @router.callback_query(F.data == "transfer:live")
    async def transfer_live_toggle(callback: CallbackQuery) -> None:
        mode = await ctx.transfer_service.toggle_live_mode()
        await callback.message.answer(f"Live transfer {'enabled' if mode else 'disabled'}")
        await callback.answer()

    @router.callback_query(F.data == "transfer:pause")
    async def transfer_pause(callback: CallbackQuery) -> None:
        await ctx.transfer_service.pause()
        await callback.message.answer("Transfer paused")
        await callback.answer()

    @router.callback_query(F.data == "transfer:resume")
    async def transfer_resume(callback: CallbackQuery) -> None:
        await ctx.transfer_service.resume()
        await callback.message.answer("Transfer resumed")
        await callback.answer()

    @router.callback_query(F.data == "transfer:cancel")
    async def transfer_cancel(callback: CallbackQuery) -> None:
        await ctx.transfer_service.cancel()
        await callback.message.answer("Transfer cancelled")
        await callback.answer()

    @router.callback_query(F.data == "transfer:progress")
    async def transfer_progress(callback: CallbackQuery) -> None:
        progress = await ctx.transfer_service.progress()
        await callback.message.answer(str(progress))
        await callback.answer()

    return router
