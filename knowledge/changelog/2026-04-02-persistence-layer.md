# 2026-04-02: Persistence Layer

Replaced the prototype's JSON-file store with a real async database. The old
design wrote sessions, jobs, and staged findings to flat files; that does not
survive concurrent writes from the bot and the scheduler at the same time.

## Engine (`gisst.db.engine`)
`Database` wraps an async SQLAlchemy 2.0 engine (`create_async_engine`) and an
`async_sessionmaker` with `expire_on_commit=False`. The default URL is
`sqlite+aiosqlite:///./data/gisst.db`, but the layer is Postgres-ready (the URL
is the only thing that changes).

For SQLite it registers a `connect` event that sets `PRAGMA journal_mode=WAL` and
`PRAGMA foreign_keys=ON` on every connection, so the prototype behaves like a
real database under the bot+scheduler concurrency it is about to see.

A `session()` async context manager yields a session, commits on success, rolls
back on any exception. `create_all()` builds tables from metadata for dev/test
(prod will use Alembic, landing later). `healthcheck()` runs `SELECT 1` for the
dashboard.

## ORM (`gisst.db.base`, `gisst.db.models`)
SQLAlchemy 2.0 declarative with `Mapped[...]` / `mapped_column`. Rows:
`SessionRow`, `ScheduleJobRow`, `StagedFindingRow`, `FindingRow`, `DigestRow`,
`AllowedGroupRow`. List-valued fields (keywords, sources, tags, platform
priority) are JSON-encoded into text columns: a deliberate prototype shortcut;
they become real columns / a related table if we ever query into them.

## Repository layer (`gisst.db.repositories`)
The boundary. Callers (queue, scheduler, Telegram handlers, API) never touch
SQLAlchemy: they pass and receive Pydantic models and primitives. One
repository per aggregate:
- `SessionRepository`: `user_id -> session_id` for Claude session resume.
- `ScheduleJobRepository`: Watchout job CRUD, `list_active`, `find_by_prefix`
  (short-id lookups from Telegram), `toggle`, and `touch(job_id, "last_crawl" |
  "last_digest")` for run bookkeeping.
- `StagingRepository`: `add` returns the running count for the day; `list_for_day`,
  `clear`.
- `ResearchRepository`: `record_finding`, `record_digest`, plus
  `list_recent_*` / `count_*` read models for the dashboard.
- `GroupRepository`: Telegram group allowlist.

`Repositories(db)` bundles all five so the composition root passes one object
around instead of six, and exposes `async stats()` for the dashboard
(findings / digests / active jobs / total jobs / groups).

## Why now
Persistence had to land before the agent runtime, because session-id resume
(day 3) and the staging pipeline (day 7) both read and write through these
repositories.
