"""SQLAlchemy ORM tables.

Mapped 1:1 to the Pydantic domain models, but with the bookkeeping a persistent
store needs (autoincrement ids, timestamps, JSON columns for list fields). The
repository layer converts between these ORM rows and the framework-agnostic
domain models.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from gisst.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SessionRow(Base):
    """``user_id -> claude_session_id`` (one resumable session per user)."""

    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class ScheduleJobRow(Base):
    """A Watchout Protocol job and its run history."""

    __tablename__ = "schedule_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    keywords: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    cadence: Mapped[str] = mapped_column(String(64), default="every 4h")
    digest_time: Mapped[str] = mapped_column(String(16), default="20:00")
    digest_timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    lookback_window: Mapped[str] = mapped_column(String(32), default="24h")
    platform_priority: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    chat_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    last_crawl: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_digest: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class StagedFindingRow(Base):
    """Crawl output accumulated between digests, partitioned by job + day."""

    __tablename__ = "staged_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    day: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    crawl_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class FindingRow(Base):
    """A persisted research/crawl finding (mirror of what is synced to Notion)."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    topic: Mapped[str] = mapped_column(String(256), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    key_findings: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    sources: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    finding_type: Mapped[str] = mapped_column(String(32), default="Research", index=True)
    researcher: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notion_page_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class DigestRow(Base):
    """A synthesized daily digest."""

    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    finding_count: Mapped[int] = mapped_column(Integer, default=0)
    schedule_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    notion_page_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class AllowedGroupRow(Base):
    """Telegram groups that have opted in via ``/register``."""

    __tablename__ = "allowed_groups"
    __table_args__ = (UniqueConstraint("chat_id", name="uq_allowed_groups_chat_id"),)

    chat_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    registered_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
