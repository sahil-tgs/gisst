# Gisst — AI Research Agent

## What is this?
Gisst is an AI research agent that lives in Telegram. It uses Claude Code CLI as its runtime, connects to Telegram Bot API for user interaction, syncs findings to Notion as a knowledge base, and runs scheduled research jobs (Watchout Protocol).

## Stack
- **Runtime**: Bun + TypeScript (NEVER npm/npx/yarn — always bun)
- **Agent**: Claude Code CLI via `claude -p` with `--resume` for session persistence, `--dangerously-skip-permissions`
- **Tools**: Native WebSearch + WebFetch (all tools available via --dangerously-skip-permissions)
- **Interface**: Telegram Bot API via grammy (polling-based, no webhooks needed)
- **Knowledge Base**: Notion API — auto-creates Research Findings + Daily Digests databases
- **Scheduler**: Built-in cron-like system for recurring research (Watchout Protocol)
- **Storage**: JSON files (prototype), designed for SQLite migration later

## Architecture
```
Telegram (grammy polling) → Message Handler → Agent Queue → claude -p (CLI)
                                                   ↓              ↓
                                            Telegram reply   Notion sync
                                                   ↑
Scheduler (every 60s) → Crawl Jobs → claude -p (headless) → Staging → Digest → Telegram + Notion
```

## Project Structure
```
gisst/
├── CLAUDE.md              ← you are here
├── README.md              ← product spec / vision doc
├── .gitignore
├── knowledge/             ← project knowledge base (changelogs, todos, research, design, ops)
├── scripts/               ← setup & utility scripts
│   ├── setup-vm.sh        ← one-shot VM provisioning
│   ├── setup-notion.ts    ← one-time Notion database creation
│   └── test-agent.ts      ← CLI test harness (no Telegram needed)
└── src/                   ← ALL code lives here
    ├── package.json
    ├── tsconfig.json
    ├── .env.example
    ├── index.ts            ← entry point: starts Telegram bot + scheduler + Notion setup
    ├── config.ts           ← central config from env vars
    ├── data/               ← runtime data (gitignored)
    ├── utils/
    │   └── fs.ts           ← JSON file I/O (works in both Bun and Node)
    ├── agent/
    │   ├── agent-config.ts ← user-configurable agent settings (identity, research, schedule)
    │   ├── claude.ts       ← Claude CLI spawner (--resume, --dangerously-skip-permissions)
    │   ├── prompt.ts       ← two-layer prompt: base DNA + user config layer + Watchout prompts
    │   ├── queue.ts        ← per-user message queue (sequential per user, parallel across users)
    │   └── sessions.ts     ← userId → sessionId mapping
    ├── telegram/
    │   └── client.ts       ← grammy bot: commands, group management, message routing
    ├── notion/
    │   ├── client.ts       ← Notion API wrapper
    │   ├── schema.ts       ← database creation + ID persistence
    │   └── sync.ts         ← sync research/crawl/digest to Notion
    └── scheduler/
        ├── index.ts        ← scheduler loop (ticks every 60s, checks for due jobs)
        ├── jobs.ts         ← schedule job CRUD
        └── staging.ts      ← crawl result accumulation before digest
```

## Key Patterns
- Agent outputs `[SAVE_TO_NOTION: {...}]` markers → parsed by queue.ts → pushed to Notion
- Two-layer prompt: base layer (hardcoded DNA) + user layer (dynamic from agent config)
- Per-user message queue — no concurrent Claude calls to same session
- Session persistence via `--resume` (not `--session-id`) — Claude creates session on first call
- Scheduler runs alongside bot — non-blocking `bot.start()`, scheduler ticks every 60s
- Notion databases auto-created on first boot if credentials are set

## Current State (2026-04-01)
Prototype is live on scraper-vm. Telegram bot, scheduler, and Notion are all connected.
See `knowledge/changelog/` for detailed history and `knowledge/todos/current.md` for next steps.

## For New Sessions
If you're picking up work on this project:
1. Read `knowledge/todos/current.md` for what's in progress
2. Read the latest files in `knowledge/changelog/` for recent changes
3. Check `knowledge/todos/open-questions.md` for unresolved decisions
4. Read `knowledge/design/` for architecture decisions and feature designs

## Deployment
- **VM**: scraper-vm (GCP, us-east1-b, e2-medium)
- **tmux session**: `gisst`
- **Connect**: `gcloud compute ssh scraper-vm --zone=us-east1-b -- tmux attach -t gisst`
- **Setup**: `bash scripts/setup-vm.sh`
- **Env vars**: TELEGRAM_BOT_TOKEN, NOTION_API_KEY, NOTION_PAGE_ID, CLAUDE_MODEL
