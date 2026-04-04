"""Aggregation of the Telegram routers.

The bot includes routers in registration order. Commands come first so that
slash commands are matched before the catch-all free-text handler ever sees
them.
"""

from __future__ import annotations

from aiogram import Router

from gisst.telegram.routers.commands import router as commands_router
from gisst.telegram.routers.messages import router as messages_router


def get_routers() -> list[Router]:
    """Return the routers to include on the dispatcher, in priority order."""
    return [commands_router, messages_router]


__all__ = ["get_routers"]
