"""Repository round-trips against a real temp SQLite database (the ``repos``
fixture in conftest). Every test here is async and exercises the public method
signatures of the five repositories plus the ``stats`` aggregate."""

from __future__ import annotations

from gisst.db.repositories import Repositories
from gisst.models.research import ResearchFinding, ResearchSource
from gisst.models.schedule import ScheduleJobState


def _job(topic: str = "AI safety", chat_id: str = "chat-1") -> ScheduleJobState:
    return ScheduleJobState(
        topic=topic,
        keywords=["alignment", "rlhf"],
        chat_id=chat_id,
        created_by="user-1",
    )


# -- Sessions -------------------------------------------------------------------


async def test_sessions_round_trip(repos: Repositories) -> None:
    assert await repos.sessions.get("u1") is None

    await repos.sessions.set("u1", "sess-abc")
    assert await repos.sessions.get("u1") == "sess-abc"

    # set is an upsert: a second set overwrites.
    await repos.sessions.set("u1", "sess-def")
    assert await repos.sessions.get("u1") == "sess-def"

    await repos.sessions.delete("u1")
    assert await repos.sessions.get("u1") is None


# -- Schedule jobs --------------------------------------------------------------


async def test_jobs_add_and_get(repos: Repositories) -> None:
    job = _job()
    await repos.jobs.add(job)
    fetched = await repos.jobs.get(job.id)
    assert fetched is not None
    assert fetched.topic == "AI safety"
    assert fetched.keywords == ["alignment", "rlhf"]
    assert fetched.chat_id == "chat-1"


async def test_jobs_list_active(repos: Repositories) -> None:
    active = _job(topic="active")
    inactive = _job(topic="inactive")
    inactive.active = False
    await repos.jobs.add(active)
    await repos.jobs.add(inactive)

    active_jobs = await repos.jobs.list_active()
    topics = {j.topic for j in active_jobs}
    assert "active" in topics
    assert "inactive" not in topics


async def test_jobs_toggle(repos: Repositories) -> None:
    job = _job()
    await repos.jobs.add(job)
    assert job.active is True

    toggled = await repos.jobs.toggle(job.id)
    assert toggled is not None
    assert toggled.active is False
    # Persisted, not just returned.
    reread = await repos.jobs.get(job.id)
    assert reread is not None and reread.active is False

    assert await repos.jobs.toggle("does-not-exist") is None


async def test_jobs_find_by_prefix(repos: Repositories) -> None:
    job = _job()
    await repos.jobs.add(job)
    found = await repos.jobs.find_by_prefix(job.short_id)
    assert found is not None
    assert found.id == job.id

    assert await repos.jobs.find_by_prefix("zzzzzzzz") is None


async def test_jobs_remove(repos: Repositories) -> None:
    job = _job()
    await repos.jobs.add(job)
    assert await repos.jobs.remove(job.id) is True
    assert await repos.jobs.get(job.id) is None
    # Removing a missing row reports False.
    assert await repos.jobs.remove(job.id) is False


async def test_jobs_touch_sets_timestamp(repos: Repositories) -> None:
    job = _job()
    await repos.jobs.add(job)
    assert (await repos.jobs.get(job.id)).last_crawl is None

    await repos.jobs.touch(job.id, "last_crawl")
    refreshed = await repos.jobs.get(job.id)
    assert refreshed is not None
    assert refreshed.last_crawl is not None
    assert refreshed.last_digest is None


# -- Staging --------------------------------------------------------------------


async def test_staging_add_increments_and_lists(repos: Repositories) -> None:
    day = "2026-06-25"
    assert await repos.staging.add("job-1", "first crawl", day=day) == 1
    assert await repos.staging.add("job-1", "second crawl", day=day) == 2

    staged = await repos.staging.list_for_day("job-1", day=day)
    assert [s.content for s in staged] == ["first crawl", "second crawl"]


async def test_staging_is_partitioned_by_job_and_day(repos: Repositories) -> None:
    await repos.staging.add("job-1", "a", day="2026-06-25")
    await repos.staging.add("job-2", "b", day="2026-06-25")
    await repos.staging.add("job-1", "c", day="2026-06-26")

    day25 = await repos.staging.list_for_day("job-1", day="2026-06-25")
    assert [s.content for s in day25] == ["a"]


async def test_staging_clear(repos: Repositories) -> None:
    day = "2026-06-25"
    await repos.staging.add("job-1", "x", day=day)
    await repos.staging.clear("job-1", day=day)
    assert await repos.staging.list_for_day("job-1", day=day) == []


# -- Research / digests ---------------------------------------------------------


async def test_research_record_finding_and_count(repos: Repositories) -> None:
    assert await repos.research.count_findings() == 0

    finding = ResearchFinding(
        title="Quantum leap",
        topic="Quantum",
        summary="Big news.",
        key_findings=["k1", "k2"],
        sources=[ResearchSource(title="Nature", url="https://nature.com")],
        tags=["physics"],
    )
    new_id = await repos.research.record_finding(finding, researcher="Alice")
    assert isinstance(new_id, int)
    assert await repos.research.count_findings() == 1

    recent = await repos.research.list_recent_findings()
    assert len(recent) == 1
    assert recent[0].title == "Quantum leap"
    assert recent[0].researcher == "Alice"


async def test_research_record_digest_and_list_recent(repos: Repositories) -> None:
    assert await repos.research.count_digests() == 0

    await repos.research.record_digest(
        topic="AI",
        summary="Daily roundup.",
        finding_count=3,
        schedule_id="sched-1",
    )
    assert await repos.research.count_digests() == 1

    digests = await repos.research.list_recent_digests()
    assert len(digests) == 1
    assert digests[0].topic == "AI"
    assert digests[0].finding_count == 3
    assert digests[0].schedule_id == "sched-1"


# -- Groups ---------------------------------------------------------------------


async def test_groups_add_is_allowed_and_list(repos: Repositories) -> None:
    assert await repos.groups.is_allowed("g1") is False

    await repos.groups.add("g1", registered_by="user-1")
    assert await repos.groups.is_allowed("g1") is True

    # add is idempotent - a second add does not duplicate.
    await repos.groups.add("g1")
    assert await repos.groups.list_all() == ["g1"]


# -- Aggregate stats ------------------------------------------------------------


async def test_stats_aggregate(repos: Repositories) -> None:
    await repos.jobs.add(_job(topic="t1"))
    await repos.research.record_finding(ResearchFinding(title="f"))
    await repos.research.record_digest("AI", "summary", 1)
    await repos.groups.add("g1")

    stats = await repos.stats()
    assert stats == {
        "findings": 1,
        "digests": 1,
        "active_jobs": 1,
        "total_jobs": 1,
        "groups": 1,
    }
