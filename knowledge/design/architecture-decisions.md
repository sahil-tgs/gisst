# Architecture Decisions

ADR-style record of the load-bearing choices. Each entry is a decision, the
context, and the trade-off accepted. Newest concerns at the bottom of their day.

## ADR-001 (2026-04-01): uv for packaging and environments
**Decision**: `uv` for dependency resolution, virtualenvs, and locking; `src/`
layout; console entry point in `pyproject.toml`.
**Why**: One fast tool replaces pip + venv + pip-tools. A committed `uv.lock`
makes `uv sync` reproducible for any contributor and for CI/Docker. `src/` layout
forces imports to go through the installed package (`from gisst.x import y`), so
tests exercise the same import paths as production.
**Trade-off**: uv is younger than pip. Mitigated by it being a drop-in for the
workflows we use and by pinning everything in the lockfile.

## ADR-002 (2026-04-02): Async SQLAlchemy 2.0 over the JSON store
**Decision**: Replace the prototype's JSON files with async SQLAlchemy 2.0 +
`aiosqlite`, fronted by a repository layer. Default `sqlite+aiosqlite`,
Postgres-ready via `DATABASE_URL`.
**Why**: The bot worker and the scheduler write concurrently (a digest delivery
and an incoming message can land in the same second). JSON files have no
transactions and lose writes under that. SQLAlchemy gives transactions, a real
session lifecycle, and a migration path to Postgres with zero call-site changes.
The async engine keeps DB I/O off the blocking path on the single event loop.
**Why the repository layer**: callers speak Pydantic models, never SQLAlchemy.
We can change the storage engine without touching the queue, scheduler, or API.
**Trade-off**: more ceremony than reading a dict from a file. Worth it the first
time two writers race. SQLite WAL + `foreign_keys=ON` pragmas make the prototype
behave under concurrency.

## ADR-003 (2026-04-03 / 04): Dual agent runtime behind one Protocol
**Decision**: Define an `AgentRuntime` Protocol (`run(AgentRequest) ->
AgentResult`) and ship two implementations: a Claude Code **CLI** backend and a
native Anthropic **SDK** backend. `AGENT_BACKEND` selects one.
**Why**: They have opposite trade-offs and we did not want to bet the
architecture on either.
- CLI: rides the user's Claude Code plan (cheap), gets WebSearch / WebFetch /
  Bash for free, session resume built in. Costs a process spawn per turn and
  needs an interactive `claude login`.
- API: faster, fully programmatic, deployable with just an API key (good for a
  headless VM / container), runs an explicit tool-use loop. Metered cost; we own
  the tool implementations and the conversation state.
Putting both behind one Protocol means the queue, scheduler, and prompt engine
are written once. Marker parsing and Notion sync live *above* the runtime so
backends stay focused on "talk to Claude".
**Trade-off**: two code paths to keep in sync. Bounded by the narrow Protocol
surface (`name`, `run`).

## ADR-004 (2026-04-04): aiogram v3 for Telegram
**Decision**: `aiogram` v3 (async, router-based), long-polling.
**Why**: Native `asyncio` so it shares the one event loop with the DB, scheduler,
and API: no thread bridging. v3's `Router`/filter model maps cleanly onto our
split of command router vs. message router vs. group gating. Long-polling means
no public webhook endpoint, TLS, or tunnel for the prototype.
**Trade-off**: polling has marginally higher latency and holds an outbound
connection vs. webhooks. Negligible at this scale; webhooks are on the roadmap if
we need horizontal scale.

## ADR-005 (2026-04-04): The Notifier protocol
**Decision**: Outbound producers (queue worker, digest pipeline) depend on a
one-method `Notifier` Protocol (`send_text(chat_id, text)`), not on the Telegram
adapter. The composition root injects `TelegramNotifier`.
**Why**: Keeps the dependency graph acyclic: `scheduler -> core.Notifier`, never
`scheduler -> telegram`. The scheduler must not import a channel; a channel may
import core. It also makes a second channel (Discord, Slack) a new `Notifier`
implementation with no change to the producers, and makes tests trivial with a
`RecordingNotifier`.
**Trade-off**: one extra indirection. Cheap, and it is the thing that stops the
package turning into a cycle.

## ADR-006 (2026-04-06): APScheduler 3.x, not the 4.0 alpha
**Decision**: APScheduler **3.x** with an async scheduler and a DB-backed job
store. Explicitly not 4.0.
**Why**: 4.0 was still alpha with an unstable API and a different persistence
model; a portfolio/prototype should not pin to a moving target. 3.x is stable,
well documented, runs an async scheduler on our event loop, and persists job
definitions so they survive restarts. We only need cadence firing and
at-or-past-due digest timing, which 3.x covers.
**Trade-off**: we forgo 4.0's newer API. Migration, if ever, is isolated to the
scheduler service module.

## ADR-007 (2026-04-08): FastAPI for read-only observability
**Decision**: A small FastAPI app exposing health, stats, and recent
findings/digests/jobs, run in-process with the bot.
**Why**: We already have async repositories returning read models; FastAPI turns
them into JSON endpoints and a status page with almost no glue, and gives us a
liveness/readiness probe for Docker. Read-only by design: no business logic
leaks into the web layer.
**Trade-off**: another server in the process. Guarded by `api.enabled` and bound
to config host/port.
