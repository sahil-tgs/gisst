# 2026-04-01 — Initial Agent Core Built

## What was done
- Created project skeleton with clean separation: code in `src/`, context in `knowledge/`, meta at root
- Built the core agent system:
  - `src/config.ts` — Central config, all values from env vars, data dirs under `src/data/`
  - `src/agent/sessions.ts` — Session persistence (userId → sessionId mapping, JSON file storage)
  - `src/agent/agent-config.ts` — Full user-configurable agent config (identity, research settings, interaction settings, schedule/Watchout Protocol settings)
  - `src/agent/prompt.ts` — Two-layer prompt system: hardcoded base DNA + dynamic user config layer. Includes Watchout Protocol crawl/digest prompt builders.
  - `src/agent/claude.ts` — Claude Code CLI spawner via `claude -p` with `--session-id`. Parses `[SAVE_TO_NOTION: {...}]` markers from output. Supports headless mode for Watchout background crawls.
- Created `scripts/test-agent.ts` — CLI test harness to test agent without WhatsApp
- Created `scripts/setup-vm.sh` — One-shot VM provisioning (installs bun, claude, deps, creates dirs)

## Architecture decisions
- Agent runtime = Claude Code CLI (user's $200/mo plan), not API
- WhatsApp Cloud API chosen over Baileys (ban risk)
- Native WebSearch + WebFetch + Jina Reader for research (no extra search API deps)
- Notion API for knowledge base (`@notionhq/client` is only external dep)
- JSON file storage for prototype, schema designed for SQLite migration

## What's NOT built yet
- WhatsApp integration (webhook, sender, types)
- Notion integration (client, sync, schema, setup script)
- Context management (user profiles, conversation metadata)
- Watchout Protocol scheduler (cron/interval system)
- Message queue (per-user sequential processing)
- `index.ts` entry point (Bun.serve)

## Next steps
- Push to VM, test agent core via CLI test harness
- Iterate on prompt quality based on test results
- Then: WhatsApp integration → Notion sync → Watchout Protocol
