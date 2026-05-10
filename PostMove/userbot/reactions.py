from __future__ import annotations

from collections.abc import Awaitable, Callable
from itertools import cycle
from typing import Any

from telethon.errors import RPCError
from telethon.tl.functions.messages import GetDiscussionMessageRequest, SendReactionRequest
from telethon.tl.types import ReactionEmoji

SafeCall = Callable[[Callable[[], Awaitable[Any]]], Awaitable[Any]]


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

    async def react_to_discussion_comments(
        self,
        channel_peer,
        channel_message_id: int,
        emojis: list[str],
        comments_limit: int,
        safe_call: SafeCall | None = None,
    ) -> int:
        if not emojis:
            return 0

        try:
            discussion = await self._invoke(
                GetDiscussionMessageRequest(peer=channel_peer, msg_id=channel_message_id),
                safe_call=safe_call,
            )
        except RPCError:
            return 0

        if not getattr(discussion, "messages", None):
            return 0
        if not getattr(discussion, "chats", None):
            return 0

        discussion_peer = discussion.chats[0]
        root_message_id = discussion.messages[0].id
        reacted = 0
        emoji_cycle = cycle(emojis)

        async for comment in self._client.iter_messages(
            discussion_peer,
            reply_to=root_message_id,
            limit=comments_limit,
        ):
            if getattr(comment, "out", False):
                continue
            emoji = next(emoji_cycle)
            try:
                await self._invoke(
                    SendReactionRequest(
                        peer=discussion_peer,
                        msg_id=comment.id,
                        reaction=[ReactionEmoji(emoticon=emoji)],
                        add_to_recent=True,
                    ),
                    safe_call=safe_call,
                )
            except RPCError:
                continue
            reacted += 1

        return reacted

    async def _invoke(self, request, safe_call: SafeCall | None) -> Any:
        if safe_call:
            return await safe_call(lambda: self._client(request))
        return await self._client(request)
