# Configuration

All configuration is read from the environment (or a `.env` file in the project root)
through `gisst.config`. Settings are typed with `pydantic-settings` v2 and grouped by
concern. Import the singleton via `get_settings()`; never construct `Settings` directly,
so every subsystem sees the same materialised config.

Copy `.env.example` to `.env` and fill in what you need. Unknown variables are ignored
(`extra="ignore"`), and matching is case-insensitive. Only `TELEGRAM_BOT_TOKEN` is
required to start the bot; Notion and the API dashboard are optional and degrade
gracefully.

This page mirrors `src/gisst/config.py` exactly. Each table lists the **env var**, its
**type**, **default**, and **effect**. The Python path in each heading is how you read it
in code (`get_settings().<group>.<field>`).

## Root

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `GISST_ENV` | `dev` \| `prod` \| `test` | `dev` | Runtime mode. Influences log format and verbosity. Read as `settings.env`. |

The root also exposes derived paths (not env vars, computed from `GISST_DATA_DIR`):

| Property | Value | Purpose |
| --- | --- | --- |
| `settings.data_dir` | `GISST_DATA_DIR` or `<repo>/data` | Root for the SQLite DB and runtime files. |
| `settings.work_dir` | `GISST_WORK_DIR` or `<data_dir>/workspace` | Working directory the agent operates in. |
| `settings.config_dir` | `<data_dir>/agents` | Agent profile storage. |
| `settings.session_dir` | `<data_dir>/sessions` | Session-related files. |
| `settings.staging_dir` | `<data_dir>/staging` | Crawl staging area. |

`settings.ensure_dirs()` creates all of the above on startup.

## Telegram (`settings.telegram`)

Env prefix `TELEGRAM_`.

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | `str` | `""` | Bot API token from @BotFather. Required to start the bot. |

`settings.telegram.enabled` is a derived property: `True` when `bot_token` is non-empty.

## Agent runtime (`settings.agent`)

No common prefix; each field has an explicit alias.

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `AGENT_BACKEND` | `cli` \| `api` | `cli` | Which backend drives Claude. `cli` shells out to the Claude Code CLI; `api` runs a native Anthropic SDK tool-use loop. |
| `CLAUDE_MODEL` | `str` | `claude-sonnet-4-6` | Model id passed to the selected backend. |
| `ANTHROPIC_API_KEY` | `str` | `""` | Anthropic API key. Required only when `AGENT_BACKEND=api`. |
| `AGENT_TIMEOUT` | `int` (seconds) | `300` | Per-run timeout for an agent turn. |
| `AGENT_MAX_TURNS` | `int` | `12` | Maximum tool-use turns for the `api` backend's loop. |
| `GISST_WORK_DIR` | `str` | `""` | Override for the agent's working directory. Empty means `<data_dir>/workspace`. |
| `GISST_DATA_DIR` | `str` | `""` | Override for the data root. Empty means `<repo>/data`. |

See [agent-runtime.md](agent-runtime.md) for what each backend does with these.

## Notion (`settings.notion`)

Env prefix `NOTION_`. Entirely optional.

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `NOTION_API_KEY` | `str` | `""` | Internal integration secret. |
| `NOTION_PAGE_ID` | `str` | `""` | Parent page id under which the databases are auto-provisioned. |
| `NOTION_RESEARCH_DB_ID` | `str` | `""` | Research Findings database id. Auto-filled after first boot; set it to reuse the database instead of re-creating it. |
| `NOTION_DIGEST_DB_ID` | `str` | `""` | Daily Digests database id. Auto-filled after first boot. |
| `NOTION_VERSION` | `str` | `2022-06-28` | Notion API version header. |

`settings.notion.enabled` is a derived property: `True` only when **both** `api_key` and
`page_id` are set. When disabled, the agent still researches and records findings
locally, it just does not mirror to Notion.

## Database (`settings.database`)

No prefix.

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `DATABASE_URL` | `str` | `sqlite+aiosqlite:///./data/gisst.db` | Async SQLAlchemy connection URL. Defaults to local SQLite (aiosqlite driver). Point at Postgres (e.g. `postgresql+asyncpg://...`) for a server deployment. |

`settings.database.is_sqlite` is a derived property: `True` when the URL starts with
`sqlite`. For SQLite, the engine enables WAL mode and foreign keys on every connection.

## Scheduler (`settings.scheduler`)

Env prefix `SCHEDULER_`. Drives the Watchout Protocol loop.

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `SCHEDULER_TICK_SECONDS` | `int` | `60` | How often the scheduler wakes to check for due crawls and digests. |
| `SCHEDULER_ENABLED` | `bool` | `true` | Master switch for scheduled research. Set `false` to run the bot without the Watchout loop. |

## API dashboard (`settings.api`)

Env prefix `API_`. Optional, read-only.

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `API_ENABLED` | `bool` | `true` | Whether the FastAPI dashboard starts alongside the bot. |
| `API_HOST` | `str` | `0.0.0.0` | Bind address. |
| `API_PORT` | `int` | `8000` | Bind port. |

See [api-dashboard.md](api-dashboard.md).

## Observability (`settings.observability`)

No prefix; explicit aliases.

| Env var | Type | Default | Effect |
| --- | --- | --- | --- |
| `LOG_LEVEL` | `str` | `INFO` | Minimum log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_JSON` | `bool` | `false` | `true` renders newline-delimited JSON logs (prod); `false` renders pretty console output (dev). |

Logging is configured once at startup via `configure_logging(level=..., json_logs=...)`,
which also routes stdlib logging (aiogram, httpx, apscheduler, aiosqlite) through the
same pipeline and quiets those noisy libraries to `WARNING`.

## A complete example `.env`

```dotenv
# Runtime mode
GISST_ENV=dev

# Telegram (required)
TELEGRAM_BOT_TOKEN=123456789:AAEjk-your-token

# Agent runtime
AGENT_BACKEND=cli
CLAUDE_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=                 # only when AGENT_BACKEND=api
AGENT_TIMEOUT=300
AGENT_MAX_TURNS=12
GISST_WORK_DIR=
GISST_DATA_DIR=

# Persistence
DATABASE_URL=sqlite+aiosqlite:///./data/gisst.db

# Notion (optional)
NOTION_API_KEY=
NOTION_PAGE_ID=
NOTION_RESEARCH_DB_ID=
NOTION_DIGEST_DB_ID=
NOTION_VERSION=2022-06-28

# Scheduler (Watchout Protocol)
SCHEDULER_TICK_SECONDS=60
SCHEDULER_ENABLED=true

# API dashboard (optional)
API_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8000

# Observability
LOG_LEVEL=INFO
LOG_JSON=false
```
