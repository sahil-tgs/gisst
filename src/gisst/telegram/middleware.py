"""aiogram middleware that enriches the logging context for inbound messages.

Binds ``chat_id`` / ``user_id`` into structlog's contextvars so every log line
emitted while a message is handled is automatically tagged, then logs the
inbound text length. Registered on the message router by the bot.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from gisst.logging import get_logger

log = get_logger("telegram.middleware")


class LoggingContextMiddleware(BaseMiddleware):
    """Bind ``chat_id``/``user_id`` contextvars and log inbound text length."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        chat_id = str(event.chat.id) if event.chat else None
        user_id = str(event.from_user.id) if event.from_user else None
        text = event.text or ""

        structlog.contextvars.bind_contextvars(chat_id=chat_id, user_id=user_id)
        try:
            log.info("inbound message", text_len=len(text))
            return await handler(event, data)
        finally:
            structlog.contextvars.unbind_contextvars("chat_id", "user_id")
