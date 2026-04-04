"""Free-text message router.

Everything that is *not* a slash command flows here. The handler normalises the
raw ``aiogram`` update into an :class:`gisst.models.InboundMessage`, applies the
group-gating rules ported from ``telegram/client.ts``, shows a live "typing"
indicator while the agent works, and finally streams the reply back chunked.

The actual agent call is delegated to the injected :class:`AgentQueue`, which
serialises per user and runs different users in parallel.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import Message

from gisst.core import split_message
from gisst.db.repositories import Repositories
from gisst.logging import get_logger
from gisst.models import ChatType, InboundMessage

if TYPE_CHECKING:
    from gisst.agent.queue import AgentQueue

log = get_logger("telegram.messages")

router = Router(name="messages")

_TYPING_REFRESH_SECONDS = 4.0

# Group trigger keywords (whole-word, case-insensitive) - ported from client.ts.
_KEYWORD_TRIGGERS = ("scout", "gisst")


def _chat_type(raw: str) -> ChatType:
    try:
        return ChatType(raw)
    except ValueError:
        return ChatType.PRIVATE


def _detect_mention(message: Message, bot_username: str | None) -> bool:
    """True if the message text contains an ``@<bot_username>`` mention entity."""
    if not bot_username or not message.text or not message.entities:
        return False
    target = f"@{bot_username}".lower()
    text = message.text
    for entity in message.entities:
        if entity.type != "mention":
            continue
        fragment = text[entity.offset : entity.offset + entity.length]
        if fragment.lower() == target:
            return True
    return False


def _has_keyword_trigger(text: str) -> bool:
    lowered = text.lower()
    return any(_word_present(lowered, kw) for kw in _KEYWORD_TRIGGERS)


def _word_present(lowered_text: str, word: str) -> bool:
    """Whole-word membership test (rough equivalent of ``\\bword\\b``)."""
    start = 0
    while True:
        idx = lowered_text.find(word, start)
        if idx == -1:
            return False
        before_ok = idx == 0 or not lowered_text[idx - 1].isalnum()
        after_idx = idx + len(word)
        after_ok = after_idx >= len(lowered_text) or not lowered_text[after_idx].isalnum()
        if before_ok and after_ok:
            return True
        start = idx + 1


async def _should_respond(inbound: InboundMessage, repos: Repositories) -> bool:
    """Group-gating decision, faithful to the original behaviour.

    Private chats always respond. Group chats respond only when the chat is
    registered *and* the message is addressed to the bot: it starts with ``!``
    or ``/``, mentions ``scout``/``gisst``, is an ``@mention`` of the bot, or is
    a reply to one of the bot's messages.
    """
    if not inbound.chat_type.is_group:
        return True

    if not await repos.groups.is_allowed(inbound.chat_id):
        return False

    if inbound.mentioned or inbound.is_reply_to_bot:
        return True

    text = inbound.text
    if text.startswith("!") or text.startswith("/"):
        return True
    return _has_keyword_trigger(text)


async def _keep_typing(message: Message) -> None:
    """Re-send the typing chat action every few seconds until cancelled."""
    bot = message.bot
    if bot is None:
        return
    try:
        while True:
            with contextlib.suppress(Exception):
                await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            await asyncio.sleep(_TYPING_REFRESH_SECONDS)
    except asyncio.CancelledError:
        return


def _build_inbound(
    message: Message, bot_username: str | None, bot_id: int | None
) -> InboundMessage:
    """Normalise a raw ``aiogram`` message into an :class:`InboundMessage`."""
    user = message.from_user
    full_name = ""
    user_id = ""
    if user is not None:
        full_name = user.first_name or ""
        if user.last_name:
            full_name = f"{full_name} {user.last_name}".strip()
        user_id = str(user.id)

    is_reply_to_bot = bool(
        bot_id is not None
        and message.reply_to_message is not None
        and message.reply_to_message.from_user is not None
        and message.reply_to_message.from_user.id == bot_id
    )

    return InboundMessage(
        chat_id=str(message.chat.id),
        chat_type=_chat_type(message.chat.type),
        user_id=user_id,
        user_name=full_name or "User",
        text=message.text or "",
        message_id=message.message_id,
        bot_username=bot_username,
        is_reply_to_bot=is_reply_to_bot,
        mentioned=_detect_mention(message, bot_username),
    )


@router.message(F.text)
async def handle_text(
    message: Message,
    queue: AgentQueue,
    repos: Repositories,
    bot_username: str | None = None,
    bot_id: int | None = None,
) -> None:
    """Route a free-text message through the agent queue and reply with the result."""
    # Slash commands are owned by the commands router; ignore them here.
    if (message.text or "").startswith("/"):
        return

    inbound = _build_inbound(message, bot_username, bot_id)

    if not await _should_respond(inbound, repos):
        return

    log.info(
        "dispatching to agent",
        user=inbound.user_name,
        preview=inbound.text[:100],
    )

    typing_task = asyncio.create_task(_keep_typing(message))

    async def on_response(text: str) -> None:
        """Deliver the agent's reply: chunked, as a reply, Markdown with plain fallback."""
        for chunk in split_message(text):
            try:
                await message.reply(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                try:
                    await message.reply(chunk, parse_mode=None)
                except Exception as exc:
                    log.warning("failed to deliver reply chunk", error=str(exc))

    try:
        await queue.enqueue(inbound, on_response)
    finally:
        typing_task.cancel()
