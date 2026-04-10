# Gisst Knowledge Base

Living documentation for the project: the build log, the design decisions, and
the forward work. Gisst is a Python AI research agent that lives in Telegram,
syncs findings to Notion, and runs scheduled research (the Watchout Protocol).
For the code-level overview see the top-level `CLAUDE.md` and `README.md`.

## Structure
- **changelog/**: dated, first-person build log of what changed and why
- **design/**: architecture decisions and feature designs
- **todos/**: current state and honest open questions
- **research/**: technical notes, comparisons, API gotchas

## Build log (changelog/)
The Python rebuild spans Apr 1-10 2026.

- `2026-04-01-bootstrap-and-foundation.md`: uv, ruff/mypy, typed config
  (pydantic-settings) + structlog, Pydantic domain models, constants
- `2026-04-02-persistence-layer.md`: async SQLAlchemy 2.0 engine + ORM +
  repository layer (replaced the JSON store)
- `2026-04-03-agent-runtime-and-prompt.md`: `AgentRuntime` Protocol, Claude
  Code CLI backend, two-layer prompt engine, `SAVE_TO_NOTION` marker parser
- `2026-04-04-channels-and-second-backend.md`: Anthropic SDK backend, per-user
  async queue, `Notifier` protocol, aiogram v3 bot + routers + group gating
- `2026-04-05-notion-and-self-fix.md`: Notion async client, auto-provisioned
  databases, sync wired into the queue; the digest-timing self-fix
- `2026-04-07-watchout-and-digest-fix.md`: APScheduler 3.x service (Apr 6) +
  Watchout crawl/staging/digest pipeline and the at-or-past digest timing fix
- `2026-04-10-docker-docs-release.md`: FastAPI dashboard (Apr 8), composition
  root + pytest + CI (Apr 9), Docker/compose/Alembic + docs (Apr 10)

## Design (design/)
- `architecture-decisions.md`: ADR-style record: why uv, why async SQLAlchemy
  over JSON, why a dual runtime behind one Protocol, why aiogram, why the Notifier
  protocol, why APScheduler 3.x and not the 4.0 alpha, why FastAPI for observability
- `watchout-protocol.md`: the scheduled-research design (crawl -> staging ->
  daily digest, the job model, the fixed digest timing)
- `scheduled-research.md`: earlier prototype-era notes on scheduled research
  (kept for history; `watchout-protocol.md` is current)

## Todos (todos/)
- `current.md`: what shipped and what is next (multi-profile, Postgres,
  webhooks, more channels, eval harness)
- `open-questions.md`: unresolved decisions, recorded rather than guessed

## Usage
Any agent picking up this project should read `todos/current.md` and the latest
changelog entries before starting, then `design/` for the architecture rationale.
Update these files as you go.
