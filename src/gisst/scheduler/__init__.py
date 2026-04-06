"""The scheduler subsystem: the Watchout Protocol pipeline.

This package runs recurring background research. :class:`SchedulerService` wraps
an APScheduler ``AsyncIOScheduler`` and ticks :class:`WatchoutEngine` on a fixed
interval; the engine fires per-job crawls and daily digests when the pure
cadence helpers (:func:`is_crawl_due`, :func:`is_digest_due`) say they are due.

Nothing here imports the Telegram adapter: delivery happens through the injected
:class:`~gisst.core.notifier.Notifier`, keeping the dependency graph acyclic.
"""

from __future__ import annotations

from gisst.scheduler.cadence import (
    DEFAULT_CADENCE_SECONDS,
    is_crawl_due,
    is_digest_due,
    parse_cadence_seconds,
    parse_time,
)
from gisst.scheduler.service import SchedulerService
from gisst.scheduler.watchout import WatchoutEngine

__all__ = [
    "DEFAULT_CADENCE_SECONDS",
    "SchedulerService",
    "WatchoutEngine",
    "is_crawl_due",
    "is_digest_due",
    "parse_cadence_seconds",
    "parse_time",
]
