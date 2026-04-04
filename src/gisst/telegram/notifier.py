"""Outbound delivery over Telegram.

:class:`TelegramNotifier` is the concrete :class:`gisst.core.Notifier` the
scheduler's digest pipeline (and any future alerting) injects. It owns no state
beyond the ``aiogram`` :class:`~aiogram.Bot` handle, and it never raises on a
single failed chunk - delivery is best-effort, mirroring the original
``sendTextToChat`` in ``telegram/client.ts``.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ParseMode

from gisst.core import Notifier, split_message
from gisst.logging import get_logger

log = get_logger("telegram.notifier")


class TelegramNotifier(Notifier):
    """Deliver plain text to a Telegram chat, chunked and best-effort.

    Implements the :class:`gisst.core.Notifier` protocol so producers depend on
    the narrow interface rather than the whole adapter.
    """

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_text(self, chat_id: str, text: str) -> None:
        """Send ``text`` to ``chat_id``.

        The body is split with :func:`gisst.core.split_message` and each chunk
        is sent first as Markdown; if Telegram rejects the entity parsing the
        chunk is retried as plain text. A failure on any one chunk is logged and
        swallowed so a malformed message can never crash the caller.
        """
        for chunk in split_message(text):
            try:
                await self._bot.send_message(chat_id, chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                try:
                    await self._bot.send_message(chat_id, chunk, parse_mode=None)
                except Exception as exc:
                    log.warning("failed to deliver chunk", chat_id=chat_id, error=str(exc))
