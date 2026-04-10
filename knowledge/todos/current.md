# Current State

## Status: v0.1 shipped (2026-04-10)

The Python rebuild is feature-complete for the prototype. Telegram channel,
dual Claude backend, Notion KB, Watchout Protocol, dashboard, tests, CI, Docker,
and Alembic migrations are all in.

### Done
- [x] Toolchain: uv, ruff, mypy (strict), pytest, pre-commit, Makefile, CI
- [x] Typed config (pydantic-settings) + structlog logging
- [x] Pydantic domain models
- [x] Async SQLAlchemy 2.0 engine + ORM + repository layer (SQLite, Postgres-ready)
- [x] `AgentRuntime` Protocol + CLI backend + Anthropic SDK backend
- [x] Two-layer prompt engine + `SAVE_TO_NOTION` marker parser
- [x] Per-user async queue (sequential per user, parallel across users)
- [x] `Notifier` protocol + aiogram v3 bot (command/message routers, group gating)
- [x] Notion async client + auto-provisioned databases + sync, wired into the queue
- [x] APScheduler 3.x service + DB-backed job store
- [x] Watchout Protocol: crawl -> staging -> daily digest (with the timing fix)
- [x] FastAPI observability dashboard
- [x] Composition root, Docker + compose, Alembic, README + diagrams

## Next up

### Multi-profile agents
Models already carry `AgentProfile.id` and `DEFAULT_PROFILE_ID`, but only the one
`Scout` profile ships. Wire profile-per-chat (or per-group): a `ProfileRepository`,
`/profile` commands, and a profile resolver in front of the prompt engine so
different chats get different personas.

### Postgres in earnest
Storage is engine-agnostic via `DATABASE_URL`. Run the suite against Postgres in
CI, validate the Alembic migrations there, move the JSON-in-text list columns to
real columns or a related table once we actually query into them.

### Webhooks
Swap Telegram long-polling for webhooks behind the FastAPI app (a shared ASGI
process), so the bot can scale horizontally and drop the held outbound poll
connection. Needs a public TLS endpoint and the aiogram webhook adapter.

### More channels
The `Notifier` protocol + router split means a second channel is mostly a new
adapter. Discord first (slash commands map cleanly), then Slack. Inbound routing
into the existing per-user queue; outbound via a new `Notifier`.

### Eval harness
A repeatable way to grade research quality: a fixed set of topics, golden-ish
expectations, scored on citation coverage, freshness, and digest usefulness. Run
it across both backends so we can compare CLI vs. API output and catch prompt
regressions in CI.

### Smaller
- [ ] Retry/backoff + dead-letter for failed agent turns and Notion writes
- [ ] Per-chat rate limiting and the profile's quiet-hours enforcement on digests
- [ ] Dashboard: per-job crawl/digest history view
- [ ] Structured cost/turn metrics from the API backend surfaced on the dashboard
