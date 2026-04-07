"""Cadence + due-time helpers (pure, no DB/clock). Covers ``parse_cadence_seconds``
units and fallback, ``is_crawl_due``, and the at-or-past ``is_digest_due``
semantics. All datetimes are constructed explicitly in UTC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gisst.models.schedule import ScheduleJobState
from gisst.scheduler.cadence import (
    DEFAULT_CADENCE_SECONDS,
    is_crawl_due,
    is_digest_due,
    parse_cadence_seconds,
)


def _job(**overrides) -> ScheduleJobState:
    """A minimal valid ScheduleJobState; overrides patch individual fields."""
    base = {
        "topic": "test topic",
        "chat_id": "chat-1",
        "created_by": "user-1",
    }
    base.update(overrides)
    return ScheduleJobState(**base)


# -- parse_cadence_seconds ------------------------------------------------------


def test_parse_cadence_hours() -> None:
    assert parse_cadence_seconds("every 4h") == 4 * 60 * 60


def test_parse_cadence_minutes() -> None:
    assert parse_cadence_seconds("every 30m") == 30 * 60


def test_parse_cadence_seconds_unit() -> None:
    assert parse_cadence_seconds("90s") == 90


def test_parse_cadence_days() -> None:
    assert parse_cadence_seconds("2d") == 2 * 24 * 60 * 60


def test_parse_cadence_empty_falls_back_to_default() -> None:
    assert parse_cadence_seconds("") == DEFAULT_CADENCE_SECONDS


def test_parse_cadence_unparseable_falls_back_to_default() -> None:
    assert parse_cadence_seconds("whenever") == DEFAULT_CADENCE_SECONDS


# -- is_crawl_due ---------------------------------------------------------------


def test_crawl_due_when_never_crawled() -> None:
    job = _job(cadence="every 1h", last_crawl=None)
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    assert is_crawl_due(job, now) is True


def test_crawl_not_due_when_recent() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    job = _job(cadence="every 1h", last_crawl=now - timedelta(minutes=10))
    assert is_crawl_due(job, now) is False


def test_crawl_due_when_cadence_elapsed() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    job = _job(cadence="every 1h", last_crawl=now - timedelta(hours=2))
    assert is_crawl_due(job, now) is True


def test_crawl_not_due_when_inactive() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    job = _job(cadence="every 1h", last_crawl=None, active=False)
    assert is_crawl_due(job, now) is False


# -- is_digest_due (at-or-past semantics) ---------------------------------------


def test_digest_not_due_before_scheduled_time() -> None:
    job = _job(digest_time="20:00", last_digest=None)
    now = datetime(2026, 6, 25, 19, 59, tzinfo=UTC)
    assert is_digest_due(job, now) is False


def test_digest_due_exactly_at_scheduled_minute() -> None:
    job = _job(digest_time="20:00", last_digest=None)
    now = datetime(2026, 6, 25, 20, 0, tzinfo=UTC)
    assert is_digest_due(job, now) is True


def test_digest_due_after_scheduled_time_late_tick() -> None:
    # A tick that lands a minute (or more) late must still deliver.
    job = _job(digest_time="20:00", last_digest=None)
    now = datetime(2026, 6, 25, 20, 5, tzinfo=UTC)
    assert is_digest_due(job, now) is True


def test_digest_not_due_when_already_sent_today() -> None:
    now = datetime(2026, 6, 25, 20, 5, tzinfo=UTC)
    job = _job(
        digest_time="20:00",
        last_digest=datetime(2026, 6, 25, 20, 0, tzinfo=UTC),
    )
    assert is_digest_due(job, now) is False


def test_digest_due_again_on_a_new_day() -> None:
    now = datetime(2026, 6, 26, 20, 1, tzinfo=UTC)
    job = _job(
        digest_time="20:00",
        last_digest=datetime(2026, 6, 25, 20, 0, tzinfo=UTC),
    )
    assert is_digest_due(job, now) is True


def test_digest_not_due_when_inactive() -> None:
    now = datetime(2026, 6, 25, 21, 0, tzinfo=UTC)
    job = _job(digest_time="20:00", last_digest=None, active=False)
    assert is_digest_due(job, now) is False
