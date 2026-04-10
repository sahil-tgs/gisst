# 2026-04-01: Bootstrap and Foundation

First day. Stood up the project skeleton and the typed foundation everything
else hangs off of.

## Toolchain
- `uv` for dependency + venv management. Lockfile committed (`uv.lock`). One
  command bootstraps a contributor: `uv sync`.
- `ruff` as both linter and formatter (line length 100). `mypy` in strict mode
  on `src/gisst`.
- `src/` layout. Package imports as `from gisst.x import y`. Console entry point
  `gisst` wired in `pyproject.toml`.
- MIT license, `.gitignore`, `.env.example`.

## Config (`gisst.config`)
Typed configuration on `pydantic-settings` v2. Split into one settings group per
concern so the env surface stays readable:
`settings.telegram`, `.agent`, `.notion`, `.database`, `.scheduler`, `.api`,
`.observability`. Each group is a `BaseSettings` instantiated via
`default_factory`, reading its own slice of the environment (mostly via
`env_prefix`, a few via explicit `validation_alias`).

Derived runtime paths are computed properties on the root `Settings`:
`data_dir`, `work_dir`, `config_dir`, `session_dir`, `staging_dir`, plus
`ensure_dirs()` which creates them all. The only public accessor is a cached
`get_settings()`: never construct `Settings()` directly, so the whole process
shares one materialised config.

## Logging (`gisst.logging`)
`structlog` wrapper. `get_logger("subsystem.name")` everywhere. Renders
key-value console output in dev, switches to JSON when `LOG_JSON=true` for the
VM. Log level from `LOG_LEVEL`.

## Domain models (`gisst.models`)
Pydantic v2 models, the vocabulary the rest of the codebase speaks in:
- `AgentProfile` and its parts (`AgentIdentity`, `ResearchSettings`,
  `InteractionSettings`, `ScheduleSettings`): the configurable persona that
  becomes the prompt's "user layer". Ships one default profile, the `Scout`
  analyst.
- Messaging: `InboundMessage`, `OutboundMessage`, `ChatType`.
- Research: `ResearchFinding` (+ `ResearchSource`), `CrawlFinding`. The finding
  model accepts the agent's camelCase JSON (`keyFindings`) as well as snake_case
  via `populate_by_name`, and coerces bare URL strings into `{title, url}` so the
  marker parser can validate raw model output directly.
- Schedule: `ScheduleJob` / `ScheduleJobState`, `StagedFinding`.

## Constants (`gisst.constants`)
Single home for the magic strings every layer has to agree on:
`NOTION_MARKER_TAG = "[SAVE_TO_NOTION:"`, `TELEGRAM_SPLIT_TARGET`,
`NOTION_TEXT_LIMIT`, `DEFAULT_PROFILE_ID`, `DEFAULT_AGENT_NAME`, the
`NOTION_TYPE_*` select values.

## Notes
This is a clean-room rewrite of an earlier TypeScript/Bun prototype. The product
shape (Telegram agent, Notion KB, scheduled research) carries over; the
implementation is Python from scratch. Decisions captured in
`knowledge/design/architecture-decisions.md`.
