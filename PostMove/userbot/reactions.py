from __future__ import annotations

from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji


class CommentReactionService:
    def __init__(self, client) -> None:
        self._client = client

    async def react_to_comment(self, peer, message_id: int, emoji: str) -> None:
        await self._client(
            SendReactionRequest(
                peer=peer,
                msg_id=message_id,
                reaction=[ReactionEmoji(emoticon=emoji)],
                add_to_recent=True,
            )
        )
