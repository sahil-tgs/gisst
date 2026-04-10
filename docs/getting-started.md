# Getting started

This guide takes you from a clean checkout to a running agent answering research
questions in Telegram, with optional Notion sync and the optional API dashboard.

Only `TELEGRAM_BOT_TOKEN` is strictly required to start. Notion and the dashboard are
optional and degrade gracefully when their credentials are absent.

## Prerequisites

- **Python 3.11+** (3.11 or 3.12).
- **[uv](https://docs.astral.sh/uv/)** for dependency management and running the app.
- A **Telegram account** (to talk to BotFather and to chat with your bot).
- One of:
  - the **Claude Code CLI** installed and logged in (default `AGENT_BACKEND=cli`), or
  - an **Anthropic API key** (for `AGENT_BACKEND=api`).

Install uv if you do not have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 1. Install

Clone and create the environment. `uv sync` reads `pyproject.toml`, resolves the lock,
and builds a `.venv` in one step.

```bash
git clone https://github.com/sahil-tgs/gisst.git
cd gisst

# runtime deps only
uv sync

# include dev tooling (ruff, mypy, pytest)
uv sync --extra dev
```

Run anything inside the environment with `uv run <command>`.

## 2. Configure the environment

Copy the example file and open it:

```bash
cp .env.example .env
```

Fill in `TELEGRAM_BOT_TOKEN` (next section). Everything else has a sensible default. The
full reference for every variable, with types, defaults, and effects, is in
[configuration.md](configuration.md). A minimal `.env` to start:

```dotenv
GISST_ENV=dev
TELEGRAM_BOT_TOKEN=123456:your-token-from-botfather
AGENT_BACKEND=cli
CLAUDE_MODEL=claude-sonnet-4-6
```

If you want the SDK backend instead of the CLI:

```dotenv
AGENT_BACKEND=api
ANTHROPIC_API_KEY=sk-ant-...
```

## 3. Create a Telegram bot with BotFather

1. In Telegram, open a chat with **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`.
3. Choose a display name (for example `Scout`) and a username ending in `bot`
   (for example `my_scout_bot`).
4. BotFather replies with an **HTTP API token** that looks like
   `123456789:AAEjk...`. Copy it into `TELEGRAM_BOT_TOKEN` in your `.env`.
5. Recommended, so the bot can read normal messages in groups: send `/setprivacy` to
   BotFather, pick your bot, and set privacy to **Disabled**. (If you leave privacy
   enabled, the bot only sees commands and replies/mentions in groups.)

No webhook setup is needed. The bot uses long polling.

## 4. First run

The app creates its runtime directories, builds the SQLite database, configures logging,
starts the Telegram bot (long polling), and starts the scheduler.

```bash
uv run gisst
```

You should see structured startup logs: database ready, bot started, scheduler running.
Leave it running in the foreground (or under a process manager / tmux session on a VM).

Open Telegram, find your bot by its username, and send:

```
/start
```

The bot introduces itself. In a private chat you can start asking questions right away.

## 5. Register a group

In a one-on-one chat the bot answers directly. In a **group**, the bot only acts in
groups that have opted in, so it does not respond to every message everywhere.

1. Add your bot to the group.
2. In the group, send:

   ```
   /register
   ```

This records the group as allowed (stored via the group repository). From then on the
bot participates in that group according to your trigger settings (`/start` and the
help text describe whether it answers all messages, only mentions, or only commands).

## 6. Send your first research query

In a private chat or a registered group, ask a real question:

```
What's the latest on the EU AI Act enforcement timeline?
```

The agent researches (web search and fetch), synthesises a cited briefing, and replies.
Long answers are split into multiple messages automatically. If the agent decides the
result is worth keeping, it appends a hidden `[SAVE_TO_NOTION: {...}]` marker; the marker
is stripped from your reply, the finding is recorded in the database, and (if Notion is
configured) pushed to your knowledge base. See
[agent-runtime.md](agent-runtime.md#the-save_to_notion-marker-contract) for the contract.

To set up recurring research, use the Watchout Protocol:

```
/schedule EU AI Act every 4h digest 20:00
```

The full command set and timing rules are in [watchout-protocol.md](watchout-protocol.md).

## 7. Optional: Notion knowledge base

Sync findings and digests into Notion as a living knowledge base.

1. Create an internal integration at
   <https://www.notion.so/my-integrations> and copy its **secret** into `NOTION_API_KEY`.
2. Create (or pick) a Notion **page** to hold the databases. Share that page with your
   integration (page menu, **Connections**, add your integration).
3. Copy the page id from its URL into `NOTION_PAGE_ID`. (The page id is the 32-character
   hex string at the end of the URL.)
4. Restart the app. On boot, Gisst auto-provisions two databases under that page:
   **Research Findings** and **Daily Digests**. Their ids are reported back; persist
   them as `NOTION_RESEARCH_DB_ID` and `NOTION_DIGEST_DB_ID` so they are reused instead
   of re-created.

```dotenv
NOTION_API_KEY=secret_...
NOTION_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# auto-filled after first boot:
NOTION_RESEARCH_DB_ID=
NOTION_DIGEST_DB_ID=
```

Notion is entirely optional. Without these keys the agent still researches, replies, and
records findings to the local database. it just does not mirror to Notion.

## 8. Optional: API dashboard

A read-only FastAPI dashboard exposes live stats, recent findings and digests, and the
state of every Watchout job. It is enabled by default and starts alongside the bot.

```dotenv
API_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8000
```

Open <http://localhost:8000/> for the dashboard, or <http://localhost:8000/health> for a
health check. Endpoints and how to run the API on its own are documented in
[api-dashboard.md](api-dashboard.md).

## Troubleshooting

- **Bot does not respond in a group.** Make sure you ran `/register` in that group and,
  if you want it to read all messages, that you disabled privacy mode in BotFather.
- **`AGENT_BACKEND=cli` errors.** Confirm the Claude Code CLI is installed and logged in
  for the user running the process. Otherwise switch to `AGENT_BACKEND=api` and set
  `ANTHROPIC_API_KEY`.
- **Nothing in Notion.** Both `NOTION_API_KEY` and `NOTION_PAGE_ID` must be set, and the
  page must be shared with the integration.
- **Verbose or unreadable logs.** Set `GISST_ENV=prod` or `LOG_JSON=true` for JSON logs,
  and tune `LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`).
