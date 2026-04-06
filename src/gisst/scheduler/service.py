"""The scheduler service - an APScheduler wrapper around :class:`WatchoutEngine`.

``SchedulerService`` owns a single ``AsyncIOScheduler`` and registers one
recurring interval job that calls :meth:`WatchoutEngine.tick` every
``settings.scheduler.tick_seconds``. The engine decides per-tick which jobs are
due; this class only concerns itself with *running the clock*.

The composition root constructs one of these, calls :meth:`start` after the
event loop is up, and :meth:`shutdown` on teardown.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from gisst.logging import get_logger
from gisst.scheduler.watchout import WatchoutEngine

if TYPE_CHECKING:
    from gisst.config import Settings

log = get_logger("scheduler.service")

# id of the single recurring tick job in APScheduler's job store.
_TICK_JOB_ID = "watchout-tick"

# Delay before the one-off post-start tick fires. Small enough to feel immediate,
# large enough that start()-then-shutdown() in tests doesn't race a live job.
_INITIAL_TICK_DELAY_SECONDS = 3


class SchedulerService:
    """Runs the Watchout engine's :meth:`tick` on a fixed interval."""

    def __init__(self, engine: WatchoutEngine, settings: Settings) -> None:
        self._engine = engine
        self._settings = settings
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._started = False

    @property
    def running(self) -> bool:
        """Whether the underlying APScheduler is currently running."""
        return self._scheduler.running

    def start(self) -> None:
        """Register the recurring tick and start the scheduler.

        Adds an interval job firing every ``tick_seconds`` and also schedules a
        single near-immediate tick so the first crawl/digest sweep doesn't wait
        a full interval after boot. Idempotent - a second call is a no-op.
        """
        if self._started:
            log.debug("scheduler already started")
            return

        interval = max(1, self._settings.scheduler.tick_seconds)

        self._scheduler.add_job(
            self._safe_tick,
            trigger="interval",
            seconds=interval,
            id=_TICK_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        # Kick off one tick shortly after start (don't block start() on it).
        run_at = datetime.now(UTC) + timedelta(seconds=_INITIAL_TICK_DELAY_SECONDS)
        self._scheduler.add_job(
            self._safe_tick,
            trigger="date",
            run_date=run_at,
            id=f"{_TICK_JOB_ID}-initial",
            replace_existing=True,
        )

        self._scheduler.start()
        self._started = True
        log.info("scheduler started", tick_seconds=interval)

    def shutdown(self, *, wait: bool = False) -> None:
        """Stop the scheduler. Safe to call when not running."""
        if not self._started:
            return
        try:
            self._scheduler.shutdown(wait=wait)
        except Exception:
            log.warning("scheduler shutdown raised", exc_info=True)
        finally:
            self._started = False
            log.info("scheduler stopped")

    async def trigger_now(self) -> None:
        """Run a single tick immediately (for tests / manual runs)."""
        await self._engine.tick()

    async def _safe_tick(self) -> None:
        """Tick wrapper that never lets an exception escape into APScheduler."""
        try:
            await self._engine.tick()
        except Exception:
            log.error("scheduler tick failed", exc_info=True)
