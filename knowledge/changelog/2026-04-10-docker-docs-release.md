# 2026-04-08 -> 10: Dashboard, Wiring, Tests, and Release

The last stretch: an observability surface, the composition root that bolts every
subsystem together, the test/CI safety net, and the packaging to ship it.

## Apr 8: FastAPI observability dashboard (`gisst.api`)
A read-only window into the running agent. FastAPI app with:
- `GET /health`: process + `Database.healthcheck()`.
- `GET /api/stats`: the `Repositories.stats()` aggregate (findings, digests,
  active/total jobs, groups).
- `GET /api/findings`, `/api/digests`, `/api/jobs`: recent rows via the
  `list_recent_*` read models (`StoredFinding` / `StoredDigest`).
- A small HTML dashboard at `/` rendering the same data.

Runs in the same process as the bot when `api.enabled` (host/port from config),
served by uvicorn. It only reads through repositories: no business logic, no
writes.

## Apr 9: Composition root, tests, CI
- **Composition root** (`gisst.app` / `main`): the one place that constructs
  concrete objects and injects them: build `Settings`, `ensure_dirs()`,
  `Database` + `create_all`, `Repositories`, pick the `AgentRuntime` from
  `agent.backend`, build the `Notion` client/sync (or skip if disabled), the
  per-user queue, the `TelegramNotifier`, the aiogram bot, the scheduler, and the
  FastAPI app. Then run bot polling + scheduler + API concurrently under one
  `asyncio` event loop with graceful shutdown (`Database.dispose()`, scheduler
  stop). Everything below this layer takes its collaborators by constructor;
  this is the only file that knows the concrete wiring.
- **pytest suite**: `pytest` + `pytest-asyncio` + `httpx`/ASGI transport.
  Coverage on the marker parser (balanced-brace edge cases, camelCase payloads,
  invalid JSON), repositories against an in-memory SQLite db, the prompt engine's
  two-layer composition, the queue's per-user serialisation, and the digest
  due-check (including the at-or-past timing fix). A `FakeRuntime` and a
  `RecordingNotifier` keep tests offline and deterministic.
- **CI**: GitHub Actions: `uv sync`, `ruff check`, `ruff format --check`,
  `mypy`, `pytest`. **pre-commit** mirrors ruff + mypy so failures surface before
  a push. A **Makefile** wraps the common targets (`make lint`, `make test`,
  `make run`, `make fmt`).

## Apr 10: Docker, migrations, docs
- **Docker**: multi-stage image (`uv` build stage -> slim runtime), non-root
  user. **docker-compose** runs the agent and (optionally) a Postgres service,
  so the SQLite -> Postgres swap is a one-line `DATABASE_URL` change.
- **Alembic**: migrations wired against the SQLAlchemy metadata. `create_all`
  stays for dev/test; prod boots via `alembic upgrade head`. Initial migration
  captures the day-2 schema.
- **Docs**: rewrote `README.md` (architecture, quickstart, configuration table,
  the two agent backends, the Watchout Protocol). Added an architecture diagram
  and a Watchout sequence diagram. `knowledge/` updated to match this build.

## State at release
Single default `Scout` profile. SQLite by default, Postgres-ready. Two
interchangeable Claude backends. Telegram channel live, Notion KB auto-provisioned,
Watchout Protocol delivering daily digests, dashboard up. Forward work in
`knowledge/todos/current.md`.
