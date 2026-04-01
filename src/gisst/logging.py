"""Structured logging via ``structlog``.

``configure_logging`` is idempotent and bridges the stdlib ``logging`` module
into structlog so third-party libraries (aiogram, httpx, apscheduler) flow
through the same pipeline. ``dev`` mode renders pretty console output; ``prod``
(or ``LOG_JSON=true``) renders newline-delimited JSON.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_CONFIGURED = False


def configure_logging(*, level: str = "INFO", json_logs: bool = False) -> None:
    """Configure structlog + stdlib logging. Safe to call more than once."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = getattr(logging, level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging through structlog formatting too.
    handler = logging.StreamHandler(sys.stderr)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    # Tame noisy libraries.
    for noisy in ("httpx", "httpcore", "apscheduler", "aiosqlite"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger, optionally namespaced."""
    return structlog.get_logger(name)
