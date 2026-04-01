"""Channel-agnostic messaging models.

The Telegram adapter translates raw ``aiogram`` updates into ``InboundMessage``
and turns agent output into ``OutboundMessage`` chunks. Keeping the agent core
ignorant of Telegram specifics makes it possible to add other channels later
(the OpenClaw philosophy - one brain, many surfaces).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ChatType(StrEnum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"

    @property
    def is_group(self) -> bool:
        return self in (ChatType.GROUP, ChatType.SUPERGROUP)


class InboundMessage(BaseModel):
    """A normalised inbound user message."""

    chat_id: str
    chat_type: ChatType
    user_id: str
    user_name: str
    text: str
    message_id: int | None = None
    bot_username: str | None = None
    is_reply_to_bot: bool = False
    mentioned: bool = False

    @property
    def is_command(self) -> bool:
        return self.text.startswith("/") or self.text.startswith("!")


class OutboundMessage(BaseModel):
    """A single message to deliver to a chat (already chunked to Telegram size)."""

    chat_id: str
    text: str
    reply_to_message_id: int | None = None
    parse_markdown: bool = True
    extra: dict[str, str] = Field(default_factory=dict)
