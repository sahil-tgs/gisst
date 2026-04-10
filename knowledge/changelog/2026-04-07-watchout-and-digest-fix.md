# 2026-04-06 & 07: Watchout Protocol, Scheduler, and the Digest Timing Fix

Two days folded together because the scheduler service and the pipeline it drives
are one story.

## Apr 6: Scheduler service (`gisst.scheduler`)
Adopted **APScheduler 3.x** with an async scheduler running on the bot's event
loop. Picked the stable 3.x line deliberately over the 4.0 alpha (rationale in
`architecture-decisions.md`). A DB-backed job store keeps schedule definitions in
SQLite via `ScheduleJobRepository`, so jobs survive restarts.

The service exposes register / pause-resume (`toggle`) / remove, ticks on
`scheduler.tick_seconds` (default 60), and on each tick asks "what is due now?"
across the active jobs. It depends on injected collaborators only: `runtime`,
`Repositories`, and a `Notifier`: never on Telegram directly.

## Apr 7: Watchout Protocol: crawl -> staging -> digest
The scheduled-research pipeline (full design in
`knowledge/design/watchout-protocol.md`).

A job has a `topic`, `keywords`, a `cadence` (how often to crawl), a
`lookback_window`, a `digest_time` + `digest_timezone`, and a delivery `chat_id`.

- **Crawl**: fires on cadence as a `headless=True` agent run with the Watchout
  crawl prompt. Claude returns a JSON array of `CrawlFinding` items; each is
  stored via `StagingRepository.add(job_id, content)`, which returns the running
  count for the day. `jobs.touch(job_id, "last_crawl")` records the run.
- **Staging**: accumulated per `(job_id, day)`. Crawls never deliver anything to
  the user; they just build up context.
- **Digest**: at `digest_time`, the day's staged findings are loaded and fed to
  the headless digest prompt. Claude synthesises one briefing; it goes to the
  `Notifier` (Telegram) as a summary and to `NotionSync` as a digest page, and is
  recorded via `ResearchRepository.record_digest(...)`. Then
  `jobs.touch(job_id, "last_digest")` and `staging.clear(...)` for the day.

## The digest timing fix
This is the bug the agent flagged on Apr 5, fixed properly here as part of the
real APScheduler-driven digest path.

Old logic fired a digest only when the current minute *exactly* matched
`digest_time`. With a 60s tick, a tick landing one minute late missed the window
and the digest never went out that day.

New logic is "at-or-past due, once per day": compute the scheduled time in the
job's `digest_timezone`, and fire when the current time is at or past it *and*
`last_digest` is not already today. The digest goes out as soon as the scheduler
sees the window has opened, and the `last_digest` guard makes it idempotent
(catch-up after a restart still fires exactly once).

Net: crawls were always working; digests now actually deliver.
