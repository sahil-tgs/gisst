# API dashboard

Gisst ships an optional, read-only FastAPI dashboard: a small window onto the running
agent. It never mutates state. It only reads through the
`gisst.db.repositories.Repositories` aggregate, so it is safe to expose internally
without auth. It surfaces live stat cards, the most recent research findings and digests,
and the state of every Watchout Protocol job.

The app is created by `gisst.api.create_api(...)` (from `gisst.api.app`) and is wired with
the same `Repositories` instance the bot and scheduler use, so the numbers are always
live, never a snapshot.

## Enabling and running

The dashboard is controlled by the `API_*` settings (see
[configuration.md](configuration.md#api-dashboard-settingsapi)):

| Env var | Default | Effect |
| --- | --- | --- |
| `API_ENABLED` | `true` | Start the dashboard alongside the bot. |
| `API_HOST` | `0.0.0.0` | Bind address. |
| `API_PORT` | `8000` | Bind port. |

With defaults, running the app starts everything together:

```bash
uv run gisst
```

Then open:

- <http://localhost:8000/> - the HTML dashboard
- <http://localhost:8000/health> - health check
- <http://localhost:8000/docs> - FastAPI's auto-generated OpenAPI docs

To run only the API (for example to inspect a database without starting the bot), serve
the app factory with uvicorn. Because `create_api` needs a `Repositories`, expose a
zero-arg factory that builds the database and repositories, then point uvicorn at it:

```bash
# build_dashboard() returns create_api(repositories) wired to the DB
uv run uvicorn gisst.api:build_dashboard --factory --host 0.0.0.0 --port 8000
```

Set `API_ENABLED=false` to keep the bot and scheduler running with no HTTP surface.

## Endpoints

All endpoints are `GET`. The `/api/*` routes return JSON; `/` returns HTML.

### `GET /health`

Liveness and dependency check. Returns the service status and whether the database
answered a probe (`Database.healthcheck()`), suitable for a load balancer or uptime
monitor.

```json
{ "status": "ok", "database": true }
```

### `GET /api/stats`

The aggregate counts behind the stat cards, straight from `Repositories.stats()`:

```json
{
  "findings": 128,
  "digests": 14,
  "active_jobs": 3,
  "total_jobs": 5,
  "groups": 2
}
```

| Key | Source |
| --- | --- |
| `findings` | `research.count_findings()` |
| `digests` | `research.count_digests()` |
| `active_jobs` | `len(jobs.list_active())` |
| `total_jobs` | `len(jobs.list_all())` |
| `groups` | `len(groups.list_all())` |

### `GET /api/findings`

The most recent research and crawl findings, newest first, from
`research.list_recent_findings(limit)` as `StoredFinding` read models. Supports an
optional `limit` query parameter (default 50).

```json
[
  {
    "id": 128,
    "title": "EU AI Act enforcement timeline",
    "topic": "AI regulation",
    "summary": "Phased enforcement across 2025-2026...",
    "finding_type": "Research",
    "researcher": "Scout",
    "notion_page_id": "1a2b3c...",
    "created_at": "2026-06-25T11:04:00Z"
  }
]
```

### `GET /api/digests`

The most recent synthesised digests, newest first, from
`research.list_recent_digests(limit)` as `StoredDigest` read models. Supports an optional
`limit` query parameter (default 50).

```json
[
  {
    "id": 14,
    "topic": "EU AI Act",
    "summary": "Today across 4 crawls: ...",
    "finding_count": 9,
    "schedule_id": "7f3a1c2e",
    "notion_page_id": "9f8e7d...",
    "created_at": "2026-06-24T20:00:00Z"
  }
]
```

### `GET /api/jobs`

Every Watchout Protocol job and its run history, from `jobs.list_all()` as
`ScheduleJobState` objects. Each entry includes the topic, cadence, digest time and
timezone, active flag, delivery `chat_id`, and the `last_crawl` / `last_digest`
timestamps.

```json
[
  {
    "id": "7f3a1c2e-...",
    "topic": "EU AI Act",
    "keywords": ["enforcement", "AI Office"],
    "cadence": "every 4h",
    "digest_time": "20:00",
    "digest_timezone": "UTC",
    "lookback_window": "24h",
    "platform_priority": ["reuters.com"],
    "active": true,
    "chat_id": "-1001234567890",
    "created_by": "42",
    "last_crawl": "2026-06-25T16:00:00Z",
    "last_digest": "2026-06-24T20:00:00Z"
  }
]
```

### `GET /`

The HTML dashboard. Renders the stat cards (from `/api/stats`), a recent-findings table,
a recent-digests list, and the job table, server-rendered from the same repository calls.
It is the human-friendly view; the `/api/*` JSON endpoints are the machine-friendly view.

## Why read-only

The dashboard deliberately has no write endpoints. State changes happen only through
Telegram (user messages, `/schedule` commands) or the scheduler. Keeping the HTTP surface
read-only means:

- exposing it internally needs no auth and carries no risk of accidental mutation,
- it can be pointed at a production database safely for observability,
- it never contends with the bot or scheduler for writes; it only reads through the same
  `Repositories` aggregate, which returns Pydantic read models (`StoredFinding`,
  `StoredDigest`) and never leaks ORM objects.
