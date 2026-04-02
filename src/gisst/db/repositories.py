"""Repository layer.

Each repository wraps the :class:`~gisst.db.engine.Database` and exposes
domain-typed methods. Callers (the queue, scheduler, Telegram handlers, API)
never touch SQLAlchemy directly - they receive Pydantic models and primitives.

``Repositories`` is a small aggregate so the composition root can pass one
object around instead of six.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy import delete, func, select

from gisst.db.engine import Database
from gisst.db.models import (
    AllowedGroupRow,
    DigestRow,
    FindingRow,
    ScheduleJobRow,
    SessionRow,
    StagedFindingRow,
)
from gisst.logging import get_logger
from gisst.models.research import ResearchFinding, StoredDigest, StoredFinding
from gisst.models.schedule import ScheduleJobState, StagedFinding

log = get_logger("db.repositories")

TimestampField = Literal["last_crawl", "last_digest"]


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _dumps(value: Sequence[Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []


# -- Sessions ------------------------------------------------------------------


class SessionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get(self, user_id: str) -> str | None:
        async with self._db.session() as s:
            row = await s.get(SessionRow, user_id)
            return row.session_id if row else None

    async def set(self, user_id: str, session_id: str) -> None:
        async with self._db.session() as s:
            row = await s.get(SessionRow, user_id)
            if row:
                row.session_id = session_id
            else:
                s.add(SessionRow(user_id=user_id, session_id=session_id))

    async def delete(self, user_id: str) -> None:
        async with self._db.session() as s:
            await s.execute(delete(SessionRow).where(SessionRow.user_id == user_id))


# -- Schedule jobs -------------------------------------------------------------


class ScheduleJobRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    @staticmethod
    def _to_model(row: ScheduleJobRow) -> ScheduleJobState:
        return ScheduleJobState(
            id=row.id,
            topic=row.topic,
            keywords=_loads(row.keywords),
            cadence=row.cadence,
            digest_time=row.digest_time,
            digest_timezone=row.digest_timezone,
            lookback_window=row.lookback_window,
            platform_priority=_loads(row.platform_priority),
            active=row.active,
            chat_id=row.chat_id,
            created_by=row.created_by,
            last_crawl=row.last_crawl,
            last_digest=row.last_digest,
        )

    async def add(self, job: ScheduleJobState) -> None:
        async with self._db.session() as s:
            s.add(
                ScheduleJobRow(
                    id=job.id,
                    topic=job.topic,
                    keywords=_dumps(job.keywords),
                    cadence=job.cadence,
                    digest_time=job.digest_time,
                    digest_timezone=job.digest_timezone,
                    lookback_window=job.lookback_window,
                    platform_priority=_dumps(job.platform_priority),
                    active=job.active,
                    chat_id=job.chat_id,
                    created_by=job.created_by,
                    last_crawl=job.last_crawl,
                    last_digest=job.last_digest,
                )
            )
        log.info("schedule job added", topic=job.topic, cadence=job.cadence)

    async def get(self, job_id: str) -> ScheduleJobState | None:
        async with self._db.session() as s:
            row = await s.get(ScheduleJobRow, job_id)
            return self._to_model(row) if row else None

    async def list_all(self) -> list[ScheduleJobState]:
        async with self._db.session() as s:
            rows = (await s.execute(select(ScheduleJobRow))).scalars().all()
            return [self._to_model(r) for r in rows]

    async def list_active(self) -> list[ScheduleJobState]:
        async with self._db.session() as s:
            stmt = select(ScheduleJobRow).where(ScheduleJobRow.active.is_(True))
            rows = (await s.execute(stmt)).scalars().all()
            return [self._to_model(r) for r in rows]

    async def list_for_chat(self, chat_id: str) -> list[ScheduleJobState]:
        async with self._db.session() as s:
            stmt = select(ScheduleJobRow).where(ScheduleJobRow.chat_id == chat_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [self._to_model(r) for r in rows]

    async def find_by_prefix(self, prefix: str) -> ScheduleJobState | None:
        async with self._db.session() as s:
            stmt = select(ScheduleJobRow).where(ScheduleJobRow.id.like(f"{prefix}%"))
            row = (await s.execute(stmt)).scalars().first()
            return self._to_model(row) if row else None

    async def remove(self, job_id: str) -> bool:
        async with self._db.session() as s:
            row = await s.get(ScheduleJobRow, job_id)
            if not row:
                return False
            await s.delete(row)
            return True

    async def toggle(self, job_id: str) -> ScheduleJobState | None:
        async with self._db.session() as s:
            row = await s.get(ScheduleJobRow, job_id)
            if not row:
                return None
            row.active = not row.active
            return self._to_model(row)

    async def touch(self, job_id: str, field: TimestampField) -> None:
        async with self._db.session() as s:
            row = await s.get(ScheduleJobRow, job_id)
            if row:
                setattr(row, field, datetime.now(UTC))


# -- Staging -------------------------------------------------------------------


class StagingRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add(self, job_id: str, content: str, *, day: str | None = None) -> int:
        day = day or _today()
        async with self._db.session() as s:
            s.add(StagedFindingRow(job_id=job_id, day=day, content=content))
            await s.flush()
            count = await s.scalar(
                select(func.count())
                .select_from(StagedFindingRow)
                .where(StagedFindingRow.job_id == job_id, StagedFindingRow.day == day)
            )
        total = int(count or 0)
        log.info("finding staged", job_id=job_id, total_today=total)
        return total

    async def list_for_day(self, job_id: str, *, day: str | None = None) -> list[StagedFinding]:
        day = day or _today()
        async with self._db.session() as s:
            stmt = (
                select(StagedFindingRow)
                .where(StagedFindingRow.job_id == job_id, StagedFindingRow.day == day)
                .order_by(StagedFindingRow.crawl_time)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [StagedFinding(crawl_time=r.crawl_time, content=r.content) for r in rows]

    async def clear(self, job_id: str, *, day: str | None = None) -> None:
        day = day or _today()
        async with self._db.session() as s:
            await s.execute(
                delete(StagedFindingRow).where(
                    StagedFindingRow.job_id == job_id, StagedFindingRow.day == day
                )
            )


# -- Research / digests --------------------------------------------------------


class ResearchRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def record_finding(
        self,
        finding: ResearchFinding,
        *,
        researcher: str | None = None,
        finding_type: str = "Research",
        notion_page_id: str | None = None,
    ) -> int:
        async with self._db.session() as s:
            row = FindingRow(
                title=finding.title,
                topic=finding.topic,
                summary=finding.summary,
                key_findings=_dumps(finding.key_findings),
                sources=_dumps([src.model_dump() for src in finding.sources]),
                tags=_dumps(finding.tags),
                finding_type=finding_type,
                researcher=researcher,
                notion_page_id=notion_page_id,
            )
            s.add(row)
            await s.flush()
            return row.id

    async def record_digest(
        self,
        topic: str,
        summary: str,
        finding_count: int,
        schedule_id: str | None = None,
        notion_page_id: str | None = None,
    ) -> int:
        async with self._db.session() as s:
            row = DigestRow(
                topic=topic,
                summary=summary,
                finding_count=finding_count,
                schedule_id=schedule_id,
                notion_page_id=notion_page_id,
            )
            s.add(row)
            await s.flush()
            return row.id

    async def list_recent_findings(self, limit: int = 50) -> list[StoredFinding]:
        async with self._db.session() as s:
            stmt = select(FindingRow).order_by(FindingRow.created_at.desc()).limit(limit)
            rows = (await s.execute(stmt)).scalars().all()
            return [StoredFinding.model_validate(r) for r in rows]

    async def list_recent_digests(self, limit: int = 50) -> list[StoredDigest]:
        async with self._db.session() as s:
            stmt = select(DigestRow).order_by(DigestRow.created_at.desc()).limit(limit)
            rows = (await s.execute(stmt)).scalars().all()
            return [StoredDigest.model_validate(r) for r in rows]

    async def count_findings(self) -> int:
        async with self._db.session() as s:
            return int(await s.scalar(select(func.count()).select_from(FindingRow)) or 0)

    async def count_digests(self) -> int:
        async with self._db.session() as s:
            return int(await s.scalar(select(func.count()).select_from(DigestRow)) or 0)


# -- Allowed groups ------------------------------------------------------------


class GroupRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def is_allowed(self, chat_id: str) -> bool:
        async with self._db.session() as s:
            return (await s.get(AllowedGroupRow, chat_id)) is not None

    async def add(self, chat_id: str, registered_by: str | None = None) -> None:
        async with self._db.session() as s:
            if await s.get(AllowedGroupRow, chat_id) is None:
                s.add(AllowedGroupRow(chat_id=chat_id, registered_by=registered_by))
                log.info("group registered", chat_id=chat_id)

    async def list_all(self) -> list[str]:
        async with self._db.session() as s:
            rows = (await s.execute(select(AllowedGroupRow.chat_id))).scalars().all()
            return list(rows)


# -- Aggregate -----------------------------------------------------------------


class Repositories:
    """Bundle of every repository over a single :class:`Database`."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.jobs = ScheduleJobRepository(db)
        self.staging = StagingRepository(db)
        self.research = ResearchRepository(db)
        self.groups = GroupRepository(db)

    async def stats(self) -> dict[str, int]:
        """Aggregate counts for the dashboard."""
        return {
            "findings": await self.research.count_findings(),
            "digests": await self.research.count_digests(),
            "active_jobs": len(await self.jobs.list_active()),
            "total_jobs": len(await self.jobs.list_all()),
            "groups": len(await self.groups.list_all()),
        }

    # `date` re-exported for callers that want to construct a day key.
    @staticmethod
    def today_key() -> str:
        return date.today().isoformat()
