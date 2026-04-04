"""The ``Notifier`` protocol.

Producers of outbound content (the scheduler's digest pipeline, future alerting)
depend on this narrow interface instead of importing the Telegram adapter
directly. The composition root injects a concrete implementation
(``gisst.telegram.notifier.TelegramNotifier``). This keeps the dependency graph
acyclic: ``scheduler -> core.Notifier`` rather than ``scheduler -> telegram``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Notifier(Protocol):
    """Anything able to deliver a plain-text message to a chat/channel id."""

    async def send_text(self, chat_id: str, text: str) -> None:
        """Deliver ``text`` to ``chat_id``, splitting into multiple messages if
        the channel imposes a length limit. Implementations should not raise on
        a single failed chunk - best-effort delivery."""
        ...
