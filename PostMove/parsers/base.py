from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ParserItem:
    source_chat: str
    target_chat: str
    message_id: int
    text: str


class Parser(Protocol):
    name: str

    async def parse(self) -> list[ParserItem]:
        ...
