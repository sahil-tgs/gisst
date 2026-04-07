"""The Watchout Protocol engine.

A :class:`WatchoutEngine` owns the two-stage background pipeline:

1. **Crawl** - on each cadence interval, ask the agent (headless) to gather the
   latest developments for a job's topic and stage the raw result.
2. **Digest** - once a day at the job's digest time, synthesise everything
   staged since the last digest into one message, deliver it to the chat, mirror
   it to Notion, persist it, and clear the staging area.

Every job's crawl/digest is fired as an independent task by :meth:`tick`, and
each side-effect is wrapped in ``try/except`` so a single failing job (or a
flaky Notion call) can never take down the scheduler loop.

Ported from ``runCrawl`` / ``runDigest`` / the scheduler loop in the original
``scheduler/index.ts``, adapted to dependency injection.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from gisst.agent.prompt import (
    build_watchout_crawl_prompt,
    build_watchout_digest_prompt,
)
from gisst.agent.runtime.base import AgentRequest, AgentRuntime
from gisst.constants import NOTION_TYPE_CRAWL
from gisst.db.repositories import Repositories
from gisst.logging import get_logger
from gisst.models.research import ResearchFinding
from gisst.models.schedule import ScheduleJobState
from gisst.scheduler.cadence import is_crawl_due, is_digest_due

if TYPE_CHECKING:
    from gisst.agent.profile import ProfileStore
    from gisst.core.notifier import Notifier
    from gisst.notion.sync import NotionSync

log = get_logger("scheduler.watchout")


class WatchoutEngine:
    """Drives scheduled crawls and daily digests for every active job."""

    def __init__(
        self,
        runtime: AgentRuntime,
        repos: Repositories,
        notion: NotionSync,
        notifier: Notifier,
        profiles: ProfileStore,
    ) -> None:
        self._runtime = runtime
        self._repos = repos
        self._notion = notion
        self._notifier = notifier
        self._profiles = profiles

    # -- Crawl ----------------------------------------------------------------

    async def run_crawl(self, job: ScheduleJobState) -> None:
        """Run one background crawl for ``job`` and stage the result.

        The crawl prompt *is* the message (headless calls carry no system
        prompt). The raw text is staged, the job's ``last_crawl`` is touched,
        and the finding is best-effort mirrored to Notion + the research log.
        """
        log.info("watchout crawl starting", topic=job.topic, job_id=job.short_id)

        prompt = build_watchout_crawl_prompt(job)
        result = await self._runtime.run(
            AgentRequest(prompt=prompt, system_prompt="", headless=True)
        )
        text = result.text.strip()
        if not text:
            log.warning("watchout crawl produced no output", job_id=job.short_id)
            return

        await self._repos.staging.add(job.id, text)
        await self._repos.jobs.touch(job.id, "last_crawl")

        # Mirror to Notion (best-effort - a sync failure must not lose the crawl).
        try:
            await self._notion.sync_crawl(job.topic, text, job.id)
        except Exception:
            log.warning("notion crawl sync failed", job_id=job.short_id, exc_info=True)

        # Persist a lightweight finding row for the dashboard/history.
        try:
            finding = ResearchFinding(
                title=f"{job.topic} - Crawl",
                topic=job.topic,
                summary=text,
            )
            await self._repos.research.record_finding(
                finding,
                researcher=job.created_by,
                finding_type=NOTION_TYPE_CRAWL,
            )
        except Exception:
            log.warning("crawl finding record failed", job_id=job.short_id, exc_info=True)

        log.info("watchout crawl done", topic=job.topic, job_id=job.short_id)

    # -- Digest ---------------------------------------------------------------

    async def run_digest(self, job: ScheduleJobState) -> None:
        """Synthesise and deliver the daily digest for ``job``.

        No-ops (after logging) when nothing was staged. Otherwise it builds the
        digest via a headless agent run, delivers it to the chat, mirrors it to
        Notion, records it, clears staging, and touches ``last_digest``.
        """
        findings = await self._repos.staging.list_for_day(job.id)
        if not findings:
            log.info(
                "watchout digest skipped - nothing staged",
                topic=job.topic,
                job_id=job.short_id,
            )
            # Still touch last_digest so we don't re-check every tick for the
            # rest of the day on an empty job.
            await self._repos.jobs.touch(job.id, "last_digest")
            return

        log.info(
            "watchout digest starting",
            topic=job.topic,
            job_id=job.short_id,
            count=len(findings),
        )

        profile = await self._profiles.get_or_create_default()
        prompt = build_watchout_digest_prompt(job, profile, findings)

        result = await self._runtime.run(
            AgentRequest(prompt=prompt, system_prompt="", headless=True)
        )
        digest = result.text.strip()
        if not digest:
            log.warning("watchout digest produced no output", job_id=job.short_id)
            return

        # Deliver to the chat (the notifier is best-effort by contract).
        try:
            await self._notifier.send_text(job.chat_id, digest)
        except Exception:
            log.warning("digest delivery failed", job_id=job.short_id, exc_info=True)

        # Mirror to Notion.
        try:
            await self._notion.sync_digest(job.topic, digest, len(findings), job.id)
        except Exception:
            log.warning("notion digest sync failed", job_id=job.short_id, exc_info=True)

        # Persist + clear staging + advance the clock.
        try:
            await self._repos.research.record_digest(job.topic, digest, len(findings), job.id)
        except Exception:
            log.warning("digest record failed", job_id=job.short_id, exc_info=True)

        await self._repos.staging.clear(job.id)
        await self._repos.jobs.touch(job.id, "last_digest")

        log.info(
            "watchout digest done",
            topic=job.topic,
            job_id=job.short_id,
            count=len(findings),
        )

    # -- Loop tick ------------------------------------------------------------

    async def tick(self) -> None:
        """Inspect every active job and fire any due crawl/digest concurrently.

        Each due action is launched as its own task so one slow job doesn't
        block others, and the whole pass plus each scheduled task is guarded so
        a single failure never kills the scheduler loop.
        """
        try:
            jobs = await self._repos.jobs.list_active()
        except Exception:
            log.warning("watchout tick: failed to list jobs", exc_info=True)
            return

        now = datetime.now(UTC)
        tasks: list[asyncio.Task[None]] = []

        for job in jobs:
            try:
                if is_crawl_due(job, now):
                    tasks.append(asyncio.create_task(self._guarded(self.run_crawl, job)))
                if is_digest_due(job, now):
                    tasks.append(asyncio.create_task(self._guarded(self.run_digest, job)))
            except Exception:
                log.warning("watchout tick: scheduling check failed", job_id=job.short_id)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def _guarded(
        action: Callable[[ScheduleJobState], Awaitable[None]], job: ScheduleJobState
    ) -> None:
        """Run ``action(job)`` swallowing (and logging) any exception."""
        try:
            await action(job)
        except Exception:
            log.error(
                "watchout job failed",
                action=action.__name__,
                job_id=job.short_id,
                topic=job.topic,
                exc_info=True,
            )
