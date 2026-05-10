from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from PostMove.bot.context import BotContext
from PostMove.bot.fsm import SettingsFSM
from PostMove.bot.keyboards import settings_keyboard


def build_settings_router(ctx: BotContext) -> Router:
    router = Router(name="settings")

    @router.message(Command("settings"))
    async def settings_panel(message: Message) -> None:
        await message.answer("Settings controls", reply_markup=settings_keyboard())

    @router.callback_query(F.data == "settings:show")
    async def settings_show(callback: CallbackQuery) -> None:
        keys = ["replacers", "deny_words", "buttons", "reactions", "delays", "flood"]
        values = {key: await ctx.settings_repo.get(key, default={}) for key in keys}
        await callback.message.answer(str(values))
        await callback.answer()

    @router.callback_query(F.data == "settings:replacer")
    async def replacer_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(SettingsFSM.waiting_replacer_old)
        await callback.message.answer("Send replacer source text")
        await callback.answer()

    @router.message(SettingsFSM.waiting_replacer_old)
    async def replacer_old(message: Message, state: FSMContext) -> None:
        await state.update_data(old=(message.text or ""))
        await state.set_state(SettingsFSM.waiting_replacer_new)
        await message.answer("Send replacer target text")

    @router.message(SettingsFSM.waiting_replacer_new)
    async def replacer_new(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        old = data.get("old", "")
        new = message.text or ""
        mapping = await ctx.settings_repo.get("replacers", default={})
        mapping[old] = new
        await ctx.settings_repo.set("replacers", mapping)
        await state.clear()
        await message.answer("Replacer saved")

    @router.callback_query(F.data == "settings:deny")
    async def deny_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(SettingsFSM.waiting_deny_word)
        await callback.message.answer("Send deny word to add")
        await callback.answer()

    @router.message(SettingsFSM.waiting_deny_word)
    async def deny_apply(message: Message, state: FSMContext) -> None:
        word = (message.text or "").strip()
        words = await ctx.settings_repo.get("deny_words", default=[])
        if word and word not in words:
            words.append(word)
        await ctx.settings_repo.set("deny_words", words)
        await state.clear()
        await message.answer("Deny word saved")

    @router.callback_query(F.data == "settings:reactions")
    async def reactions_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(SettingsFSM.waiting_reactions)
        await callback.message.answer("Send reactions as comma separated list")
        await callback.answer()

    @router.message(SettingsFSM.waiting_reactions)
    async def reactions_apply(message: Message, state: FSMContext) -> None:
        payload = [item.strip() for item in (message.text or "").split(",") if item.strip()]
        await ctx.settings_repo.set("reactions", payload)
        await state.clear()
        await message.answer("Reactions updated")

    @router.callback_query(F.data == "settings:delays")
    async def delays_start(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(SettingsFSM.waiting_delay_seconds)
        await callback.message.answer("Send delay in seconds")
        await callback.answer()

    @router.message(SettingsFSM.waiting_delay_seconds)
    async def delays_apply(message: Message, state: FSMContext) -> None:
        raw = (message.text or "").strip()
        if not raw.isdigit():
            await message.answer("Delay must be numeric")
            return
        await ctx.settings_repo.set("delays", {"transfer_delay_seconds": int(raw)})
        await state.clear()
        await message.answer("Delay updated")

    return router
