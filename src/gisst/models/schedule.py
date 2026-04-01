"""Watchout Protocol scheduling models.

``ScheduleJob`` is the user-facing definition of a recurring research job.
``ScheduleJobState`` adds the runtime bookkeeping the scheduler needs (which
chat to deliver to, who created it, and the last crawl/digest timestamps).
Ported from ``ScheduleJob`` + ``ScheduleJobWithMeta`` in the original.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def _new_id() -> str:
    return str(uuid.uuid4())


class ScheduleJob(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=_new_id)
    topic: str
    keywords: list[str] = Field(default_factory=list)
    cadence: str = "every 4h"
    digest_time: str = "20:00"
    digest_timezone: str = "UTC"
    lookback_window: str = "24h"
    platform_priority: list[str] = Field(default_factory=list)
    active: bool = True

    @property
    def short_id(self) -> str:
        return self.id[:8]


class ScheduleJobState(ScheduleJob):
    """A persisted job with delivery target and run history."""

    chat_id: str
    created_by: str
    last_crawl: datetime | None = None
    last_digest: datetime | None = None


class StagedFinding(BaseModel):
    """A single crawl result accumulated in the staging area between digests."""

    crawl_time: datetime
    content: str
