"""Pure, I/O-free cadence + due-time helpers for the Watchout Protocol.

These functions decide *when* a scheduled job should crawl or emit its digest.
They are deliberately side-effect free so they can be unit-tested in isolation
without a database, a clock, or an event loop.

Faithful port of the timing logic from the original ``scheduler/index.ts``: the
digest fires on the exact minute its scheduled ``HH:MM`` is reached.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from gisst.models.schedule import ScheduleJobState

# Default crawl cadence when a job's cadence string can't be parsed.
DEFAULT_CADENCE_SECONDS = 4 * 60 * 60  # 4 hours

# Multipliers for the suffix used in a cadence string ("every 30m" -> m -> 60).
_UNIT_SECONDS: dict[str, int] = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 24 * 60 * 60,
}

# "every 4h", "4h", "every 30 m", "every 90s", "2d" ... capture amount + unit.
_CADENCE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([smhd])", re.IGNORECASE)

# "20:00", "8:5", "09:30" - hour:minute.
_TIME_RE = re.compile(r"^\s*(\d{1,2})\s*:\s*(\d{1,2})\s*$")


def parse_cadence_seconds(cadence: str) -> int:
    """Convert a human cadence string to a number of seconds.

    Examples::

        "every 4h"  -> 14400
        "every 30m" -> 1800
        "90s"       -> 90
        "2d"        -> 172800

    Falls back to :data:`DEFAULT_CADENCE_SECONDS` (4h) for anything unparsable
    or non-positive.
    """
    if not cadence:
        return DEFAULT_CADENCE_SECONDS

    match = _CADENCE_RE.search(cadence)
    if not match:
        return DEFAULT_CADENCE_SECONDS

    amount = float(match.group(1))
    unit = match.group(2).lower()
    seconds = int(amount * _UNIT_SECONDS[unit])
    return seconds if seconds > 0 else DEFAULT_CADENCE_SECONDS


def parse_time(hhmm: str) -> tuple[int, int]:
    """Parse an ``"HH:MM"`` string into a ``(hour, minute)`` tuple.

    Out-of-range or malformed input falls back to ``(20, 0)`` (8 PM), matching
    the default digest time. Values are clamped to valid clock ranges.
    """
    match = _TIME_RE.match(hhmm or "")
    if not match:
        return (20, 0)

    hour = max(0, min(23, int(match.group(1))))
    minute = max(0, min(59, int(match.group(2))))
    return (hour, minute)


def _as_utc(moment: datetime) -> datetime:
    """Coerce a possibly-naive datetime to a UTC-aware one.

    DB timestamps are written as ``datetime.now(timezone.utc)`` (aware), but a
    caller may hand us a naive ``now``. Normalising both sides keeps the
    subtraction/comparison from raising on mixed awareness.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def is_crawl_due(job: ScheduleJobState, now: datetime) -> bool:
    """Return ``True`` when ``job`` should crawl at ``now``.

    A job is due when it is active and either has never crawled, or the elapsed
    time since its last crawl meets or exceeds its parsed cadence.
    """
    if not job.active:
        return False
    if job.last_crawl is None:
        return True

    elapsed = (_as_utc(now) - _as_utc(job.last_crawl)).total_seconds()
    return elapsed >= parse_cadence_seconds(job.cadence)


def is_digest_due(job: ScheduleJobState, now: datetime) -> bool:
    """Return ``True`` when ``job`` should emit its daily digest at ``now``.

    The digest fires when ``now`` falls on the exact ``HH:MM`` the job is
    scheduled for and a digest has not already been sent today.
    """
    if not job.active:
        return False

    now_utc = _as_utc(now)
    hour, minute = parse_time(job.digest_time)

    # Fire only on the exact minute the digest is scheduled for.
    if now_utc.hour != hour or now_utc.minute != minute:
        return False

    already_sent_today = (
        job.last_digest is not None and _as_utc(job.last_digest).date() == now_utc.date()
    )
    return not already_sent_today
