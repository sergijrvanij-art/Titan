from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from PostMove.bot.context import BotContext
from PostMove.bot.fsm import ChannelFSM
from PostMove.bot.keyboards import channels_keyboard


def build_channels_router(ctx: BotContext) -> Router:
    router = Router(name="channels")

    @router.message(Command("channels"))
    async def on_channels(message: Message) -> None:
        await message.answer("Channel controls", reply_markup=channels_keyboard())

    @router.callback_query(F.data == "channels:list")
    async def list_channels(callback: CallbackQuery) -> None:
        channels = await ctx.channels_repo.list()
        if not channels:
            await callback.message.answer("No channels configured")
        else:
            lines = [
                f"#{item['id']} {item['source_channel']} -> {item['target_channel']} ({'on' if item['enabled'] else 'off'})"
                for item in channels
            ]
            await callback.message.answer("\\n".join(lines))
        await callback.answer()

    @router.callback_query(F.data == "channels:add")
    async def add_channel_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ChannelFSM.waiting_source)
        await callback.message.answer("Send source channel username/id")
        await callback.answer()

    @router.callback_query(F.data == "channels:delete")
    async def delete_channel_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ChannelFSM.waiting_delete_id)
        await callback.message.answer("Send channel mapping id to delete")
        await callback.answer()

    @router.callback_query(F.data == "channels:toggle")
    async def toggle_channel_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ChannelFSM.waiting_toggle_id)
        await callback.message.answer("Send channel mapping id to enable/disable")
        await callback.answer()

    @router.message(ChannelFSM.waiting_source)
    async def collect_source(message: Message, state: FSMContext) -> None:
        await state.update_data(source=(message.text or "").strip())
        await state.set_state(ChannelFSM.waiting_target)
        await message.answer("Send target channel username/id")

    @router.message(ChannelFSM.waiting_target)
    async def collect_target(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            await message.answer("Cannot detect user")
            return
        data = await state.get_data()
        source = data["source"]
        target = (message.text or "").strip()
        await ctx.channels_repo.add(source, target, enabled=True)
        await ctx.audit_service.record(message.from_user.id, "channel_add", {"source": source, "target": target})
        await state.clear()
        await message.answer("Channel mapping saved")

    @router.message(ChannelFSM.waiting_delete_id)
    async def delete_channel_apply(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            await message.answer("Cannot detect user")
            return
        raw = (message.text or "").strip()
        if not raw.isdigit():
            await message.answer("Channel id must be numeric")
            return
        channel_id = int(raw)
        await ctx.channels_repo.remove(channel_id)
        await ctx.audit_service.record(message.from_user.id, "channel_delete", {"id": channel_id})
        await state.clear()
        await message.answer("Channel mapping deleted")

    @router.message(ChannelFSM.waiting_toggle_id)
    async def toggle_channel_apply(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            await message.answer("Cannot detect user")
            return
        raw = (message.text or "").strip()
        if not raw.isdigit():
            await message.answer("Channel id must be numeric")
            return
        channel_id = int(raw)
        channels = await ctx.channels_repo.list()
        row = next((item for item in channels if item["id"] == channel_id), None)
        if not row:
            await message.answer("Channel id not found")
            return
        new_enabled = not bool(row["enabled"])
        await ctx.channels_repo.update(channel_id, row["source_channel"], row["target_channel"], new_enabled)
        await ctx.audit_service.record(message.from_user.id, "channel_toggle", {"id": channel_id, "enabled": new_enabled})
        await state.clear()
        await message.answer(f"Channel mapping #{channel_id} {'enabled' if new_enabled else 'disabled'}")

    return router
