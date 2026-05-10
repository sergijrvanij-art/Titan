from __future__ import annotations

from PostMove.parsers.base import ParserItem


class NewsParser:
    def __init__(self, name: str, userbot) -> None:
        self.name = name
        self._userbot = userbot
        self._last_ids: dict[str, int] = {}

    async def parse(self) -> list[ParserItem]:
        items: list[ParserItem] = []
        mappings = await self._userbot.channel_mappings()
        for source, target in mappings:
            last_id = self._last_ids.get(source, 0)
            async for message in self._userbot.iter_messages(source, limit=25):
                if message.id <= last_id:
                    continue
                text = getattr(message, "message", "") or ""
                items.append(ParserItem(source_chat=source, target_chat=target, message_id=message.id, text=text))
                if message.id > self._last_ids.get(source, 0):
                    self._last_ids[source] = message.id
        return items
