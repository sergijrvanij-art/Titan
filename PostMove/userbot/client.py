from __future__ import annotations

import asyncio

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

from PostMove.logging.structured import get_logger
from PostMove.settings.models import TelegramSettings

LOGGER = get_logger(__name__)


class UserbotClient:
    def __init__(self, settings: TelegramSettings) -> None:
        self._settings = settings
        self._client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)
        self._on_message_callbacks = []
        self._channel_provider = None

    async def connect(self) -> None:
        await self._client.connect()
        if not await self._client.is_user_authorized():
            raise RuntimeError("Telethon session is not authorized. Login manually once.")
        LOGGER.info("userbot_connected")

    async def disconnect(self) -> None:
        await self._client.disconnect()
        LOGGER.info("userbot_disconnected")

    def set_channel_provider(self, provider) -> None:
        self._channel_provider = provider

    async def channel_mappings(self) -> list[tuple[str, str]]:
        if not self._channel_provider:
            return []
        records = await self._channel_provider.list(only_enabled=True)
        return [(item["source_channel"], item["target_channel"]) for item in records]

    async def iter_messages(self, source: str, limit: int = 100):
        async for message in self._client.iter_messages(source, limit=limit):
            yield message

    async def get_message(self, chat: str, message_id: int):
        messages = await self._client.get_messages(chat, ids=message_id)
        return messages

    async def send_text(self, target_chat: str, text: str, buttons=None):
        return await self._client.send_message(target_chat, text, buttons=buttons, link_preview=False)

    async def send_media(self, target_chat: str, file_path, caption: str | None = None, buttons=None):
        return await self._client.send_file(target_chat, file_path, caption=caption, buttons=buttons)

    async def register_live_listener(self, transfer_callback):
        if self._on_message_callbacks:
            return

        @self._client.on(events.NewMessage())
        async def handler(event):
            for callback in self._on_message_callbacks:
                await callback(event)

        self._on_message_callbacks.append(transfer_callback)

    async def safe_call(self, coro_factory):
        attempt = 0
        while True:
            try:
                return await coro_factory()
            except FloodWaitError as exc:
                attempt += 1
                sleep_for = min(exc.seconds + attempt, self._settings.flood_sleep_threshold)
                LOGGER.warning("userbot_flood_wait", seconds=sleep_for)
                await asyncio.sleep(sleep_for)
