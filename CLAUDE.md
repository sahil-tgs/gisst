# Gisst — AI Research Agent

## What is this?
Gisst is an AI research agent that lives in WhatsApp. It uses Claude Code CLI as its runtime, connects to WhatsApp Cloud API for user interaction, and syncs findings to Notion as a knowledge base.

## Stack
- **Runtime**: Bun + TypeScript (NEVER npm/npx/yarn — always bun)
- **Agent**: Claude Code CLI via `claude -p` with `--session-id` for persistence
- **Tools**: Native WebSearch + WebFetch, enhanced with Jina Reader for content extraction
- **Interface**: WhatsApp Cloud API (webhook-based)
- **Knowledge Base**: Notion API
- **Storage**: JSON files (prototype), designed for SQLite migration later

## Architecture
```
WhatsApp → Meta webhook → Bun.serve() → Agent Manager → claude -p (CLI)
                                              ↓                 ↓
                                      WhatsApp reply    Notion sync
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
│   └── test-agent.ts      ← CLI test harness (no WhatsApp needed)
└── src/                   ← ALL code lives here
    ├── package.json
    ├── tsconfig.json
    ├── .env.example
    ├── config.ts           ← central config from env vars
    ├── data/               ← runtime data (gitignored)
    └── agent/
        ├── agent-config.ts ← user-configurable agent settings (identity, research, schedule)
        ├── claude.ts       ← Claude CLI spawner + Notion marker parser
        ├── prompt.ts       ← two-layer prompt: base DNA + user config layer
        └── sessions.ts     ← userId → sessionId mapping
```

## Key Patterns
- Bun auto-loads `.env` — no dotenv needed
- Use `Bun.file()` / `Bun.write()` for file I/O
- Use native `fetch()` for HTTP (WhatsApp API, Notion API)
- WhatsApp webhook MUST return 200 within 5 seconds, then process async
- Per-user message queue — no concurrent Claude calls to same session
- Agent outputs `[SAVE_TO_NOTION: {...}]` markers for structured Notion sync
- Two-layer prompt: base layer (hardcoded DNA) + user layer (dynamic from agent config)

## Current State (2026-04-01)
Agent core is built. CLI test harness ready. Awaiting VM deployment and testing.
See `knowledge/changelog/` for detailed history and `knowledge/todos/current.md` for next steps.

## For New Sessions
If you're picking up work on this project:
1. Read `knowledge/todos/current.md` for what's in progress
2. Read the latest file in `knowledge/changelog/` for recent changes
3. Check `knowledge/todos/open-questions.md` for unresolved decisions
4. Read `knowledge/design/` for architecture decisions and feature designs

## IaC / Deployment
This project is designed to be VM-transferable. All config via env vars. Setup: `bash scripts/setup-vm.sh`
