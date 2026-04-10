# Gisst: Autonomous Research Agent

## What is this?
Gisst is a self-hosted, Claude-powered personal agent that lives in Telegram and is purpose-built for
continuous, autonomous research. It is an OpenClaw-style agent (one self-hosted brain in your chat app)
focused on a single job: research a topic, answer with citations, and keep watching topics on a schedule.
Findings sync to a Notion knowledge base, and recurring research runs through the Watchout Protocol.

## Stack
- **Language**: Python 3.11+ (3.12 pinned via `.python-version`), fully async on every I/O path, full
  type hints, ruff-clean at 100 cols.
- **Package / env**: `uv` (lockfile + managed venv). Run things with `uv run ...`.
- **Agent**: two interchangeable Claude backends behind one `AgentRuntime` protocol, selected by
  `AGENT_BACKEND`:
  - `cli`: shells out to the Claude Code CLI (`claude -p`, session via `--resume`).
  - `api`: native Anthropic Python SDK tool-use loop (`WebSearch` / `WebFetch`, capped at `AGENT_MAX_TURNS`).
- **Interface**: Telegram Bot API via `aiogram` v3 (long-polling, no webhooks).
- **Knowledge base**: Notion via `notion-client`. Research Findings + Daily Digests databases are
  auto-provisioned under `NOTION_PAGE_ID` on first boot.
- **Scheduler**: `APScheduler` 3.x in-process tick (Watchout Protocol). No external cron.
- **Persistence**: async `SQLAlchemy` 2.0 + `aiosqlite` (SQLite, WAL mode) with `Alembic` migrations.
  Repository layer keeps callers on Pydantic models, never the ORM.
- **Config**: `pydantic-settings` v2, grouped by concern, single cached `get_settings()`.
- **Dashboard**: `FastAPI` + `uvicorn` + `Jinja2`, read-only over the DB.
- **Logging**: `structlog` (`get_logger("subsystem.name")`), pretty in dev, JSON in prod.
- **Quality**: `ruff` (lint + format), `mypy` (strict), `pytest` + `pytest-asyncio` (auto mode).

## Architecture
```
Telegram (aiogram polling) -> Dispatcher -> AgentQueue (per-user) -> AgentRuntime (cli | api)
                                              ↓                          ↓
                                       Telegram reply            parse SAVE_TO_NOTION
                                              ↑                          ↓
                                              └------------- Notion sync + DB persist

Scheduler tick (60s) -> Watchout job due? -> headless AgentRuntime crawl -> Staging table
                                                                              ↓ (at digest time)
                                          Digest synth -> Notifier -> Telegram + Notion + DB

FastAPI dashboard --read-only--> DB (Repositories.stats / recent findings + digests)
```

## Project Structure
```
gisst/
├-- CLAUDE.md              <- you are here
├-- README.md             <- headline / portfolio doc
├-- pyproject.toml        <- deps, ruff, mypy, pytest config (hatchling build)
├-- .env.example
├-- .python-version       <- 3.12
├-- LICENSE
├-- knowledge/            <- project knowledge base (changelog, design, todos, ops)
└-- src/gisst/            <- ALL code (src layout, import as `from gisst.x import y`)
    ├-- __main__.py        <- entry point: wires bot + scheduler + dashboard + Notion setup
    ├-- config.py          <- grouped pydantic-settings; get_settings() singleton; derived paths
    ├-- constants.py       <- NOTION_MARKER_TAG, TELEGRAM_SPLIT_TARGET, NOTION_TEXT_LIMIT, defaults
    ├-- logging.py         <- structlog config; get_logger(name)
    ├-- models/            <- framework-agnostic Pydantic domain models
    |   ├-- agent.py        <- AgentProfile (identity / research / interaction / schedule), Tone
    |   ├-- messaging.py    <- InboundMessage, OutboundMessage, ChatType
    |   ├-- research.py     <- ResearchFinding, ResearchSource, CrawlFinding, Stored* read models
    |   └-- schedule.py     <- ScheduleJob, ScheduleJobState, StagedFinding
    ├-- core/              <- cross-cutting protocols + utils
    |   ├-- notifier.py     <- Notifier protocol (async send_text(chat_id, text))
    |   └-- text.py         <- split_message (Telegram-aware chunking)
    ├-- agent/
    |   ├-- markers.py      <- parse_notion_marker -> ParsedResponse (balanced-brace JSON scan)
    |   ├-- prompt.py       <- two-layer prompt: base DNA + persona layer + Watchout prompts
    |   ├-- queue.py        <- per-user sequential message queue over the runtime
    |   └-- runtime/
    |       ├-- base.py     <- AgentRuntime protocol, AgentRequest, AgentResult, RuntimeError_
    |       ├-- cli.py      <- Claude Code CLI backend
    |       └-- api.py      <- Anthropic SDK backend
    ├-- telegram/          <- aiogram bot, command router, group management, TelegramNotifier
    ├-- notion/            <- client wrapper, schema auto-provisioning, sync (research/crawl/digest)
    ├-- scheduler/         <- APScheduler loop + Watchout (crawl -> staging -> digest)
    ├-- api/              <- FastAPI dashboard over the DB
    └-- db/
        ├-- base.py        <- declarative Base
        ├-- engine.py      <- async engine + session factory (SQLite WAL + FK pragmas)
        ├-- models.py      <- SQLAlchemy ORM rows (sessions, schedule_jobs, staged_findings,
        |                     findings, digests, allowed_groups)
        └-- repositories.py <- typed repository layer (Repositories aggregate: sessions, jobs,
                              staging, research, groups; async .stats())
```

## Key Patterns
- **Dual runtime behind one protocol.** Both backends implement `AgentRuntime` (`name`,
  `async run(AgentRequest) -> AgentResult`). Marker parsing, Notion sync, and queueing live *above* the
  runtime, so they are backend-agnostic. Switch with `AGENT_BACKEND` only.
- **`Notifier` protocol decoupling.** The scheduler depends on `core.Notifier`
  (`async send_text(chat_id, text)`), never on the Telegram package. The composition root injects
  `TelegramNotifier`. Dependency graph stays acyclic: `scheduler -> core.Notifier`, never
  `scheduler -> telegram`.
- **Per-user message queue.** Messages are serialized per user (no concurrent Claude calls against one
  session) and parallel across users. Session ids persist via the `sessions` table and `--resume`.
- **Two-layer prompt.** A hardcoded base layer (the agent's DNA) plus a dynamic persona layer rendered
  from the `AgentProfile`, plus dedicated Watchout crawl/digest prompts. See `agent/prompt.py`.
- **Repository layer.** Callers receive Pydantic domain models and primitives, never SQLAlchemy rows.
  `Repositories` bundles `sessions / jobs / staging / research / groups` over a single `Database`.
- **Watchout tick.** Scheduler ticks every `SCHEDULER_TICK_SECONDS` (default 60). Per active job it
  checks cadence vs `last_crawl` to run headless crawls, stages results by job + day, and at the job's
  `digest_time` synthesizes and delivers a digest, then clears that day's staging.
- **`[SAVE_TO_NOTION: {...}]` marker.** The agent appends this marker; `agent/markers.py` extracts it
  with a balanced-brace scan, validates a `ResearchFinding`, strips it from the user-facing text, and the
  queue pushes the finding to Notion + the DB.

## For New Sessions
If you are picking up work on this project:
1. Read `knowledge/todos/current.md` for what is in progress.
2. Skim the latest files in `knowledge/changelog/` for recent changes.
3. Check `knowledge/todos/open-questions.md` for unresolved decisions.
4. Read `knowledge/design/` for architecture decisions and feature designs.

Before writing code, READ the foundation files you depend on (`config.py`, `constants.py`,
`models/`, `core/`, `agent/runtime/base.py`, `db/repositories.py`) so your imports and signatures match
exactly. Use `from __future__ import annotations` at the top of every module, full type hints, and prefer
dependency injection (receive `runtime` / `repos` / `notifier` via constructors).

## Commands
```bash
uv sync                    # install runtime deps
uv sync --extra dev        # + ruff / mypy / pytest
uv run python -m gisst     # run bot + scheduler + dashboard
make lint                  # ruff check + format check
make typecheck             # mypy (strict)
make test                  # pytest
```

## Deployment
- **VM**: scraper-vm (GCP, us-east1-b, e2-medium).
- **tmux session**: `gisst`.
- **Connect**: `gcloud compute ssh scraper-vm --zone=us-east1-b -- tmux attach -t gisst`.
- **Run**: `uv run python -m gisst` inside the tmux session.
- **Required env**: `TELEGRAM_BOT_TOKEN`. **Optional**: `AGENT_BACKEND`, `CLAUDE_MODEL`,
  `ANTHROPIC_API_KEY` (when `AGENT_BACKEND=api`), `NOTION_API_KEY`, `NOTION_PAGE_ID`, `DATABASE_URL`,
  `API_*`, `SCHEDULER_*`. See `.env.example` for the full surface.
