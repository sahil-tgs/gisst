"""The Telegram channel adapter (aiogram v3).

Exposes the two public entry points the composition root wires up:

* :class:`TelegramBot` - the polling bot + dispatcher that routes inbound
  messages into the agent queue.
* :class:`TelegramNotifier` - a :class:`gisst.core.Notifier` the scheduler uses
  to push digests outbound.
"""

from __future__ import annotations

from gisst.telegram.bot import TelegramBot
from gisst.telegram.notifier import TelegramNotifier

__all__ = ["TelegramBot", "TelegramNotifier"]
