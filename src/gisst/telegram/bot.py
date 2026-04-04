"""The Telegram channel adapter.

:class:`TelegramBot` wires an ``aiogram`` :class:`~aiogram.Bot` and
:class:`~aiogram.Dispatcher` to the agent queue and the repositories. Handlers
do not import these collaborators; the bot stashes them in the dispatcher's
workflow data (``dp["queue"]``, ``dp["repos"]``, ``dp["bot_username"]``,
``dp["bot_id"]``) and aiogram injects them into handlers by parameter name.

This keeps the dependency graph clean: the bot depends on the queue and repos
(injected via the constructor), never the other way around.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher

from gisst.config import Settings
from gisst.db.repositories import Repositories
from gisst.logging import get_logger
from gisst.telegram.middleware import LoggingContextMiddleware
from gisst.telegram.routers import get_routers
from gisst.telegram.routers.messages import router as messages_router

if TYPE_CHECKING:
    from gisst.agent.queue import AgentQueue

log = get_logger("telegram.bot")


class TelegramBot:
    """Owns the aiogram bot/dispatcher lifecycle and message routing."""

    def __init__(
        self,
        settings: Settings,
        queue: AgentQueue,
        repos: Repositories,
    ) -> None:
        self._settings = settings
        self._queue = queue
        self._repos = repos

        self.bot = Bot(token=settings.telegram.bot_token)
        self.dp = Dispatcher()

        # Collaborators injected into every handler by parameter name.
        self.dp["queue"] = queue
        self.dp["repos"] = repos
        self.dp["bot_username"] = None
        self.dp["bot_id"] = None

        # Logging context only needs to wrap inbound message handling.
        messages_router.message.middleware(LoggingContextMiddleware())

        for router in get_routers():
            self.dp.include_router(router)

    async def start(self) -> None:
        """Learn the bot's own identity, then poll for updates until stopped."""
        me = await self.bot.get_me()
        self.dp["bot_username"] = me.username
        self.dp["bot_id"] = me.id
        log.info("telegram bot started", username=me.username, bot_id=me.id)

        await self.dp.start_polling(self.bot)

    async def stop(self) -> None:
        """Stop polling and release the underlying HTTP session."""
        await self.dp.stop_polling()
        await self.bot.session.close()
        log.info("telegram bot stopped")
