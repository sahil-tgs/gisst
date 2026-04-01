# 2026-04-01 — Watchout Protocol (Scheduled Research)

## What was built
- **Scheduler service** (`src/scheduler/index.ts`) — Runs every 60s, checks for due crawl and digest jobs
- **Staging system** (`src/scheduler/staging.ts`) — Accumulates crawl findings in `data/staging/{jobId}/{date}.json`
- **Job management** (`src/scheduler/jobs.ts`) — CRUD for scheduled jobs, stored in `data/agents/schedule-jobs.json`
- **Telegram commands** for schedule management:
  - `/schedule <topic> [every Xh] [digest HH:MM]` — create a scheduled job
  - `/schedules` — list all jobs for this chat
  - `/pause <id>` — toggle a job active/paused
  - `/remove <id>` — delete a job

## How it works
1. User creates a schedule via `/schedule F1 News every 4h digest 20:00`
2. Scheduler ticks every 60s, checks if any crawl is due (based on cadence)
3. When due: spawns `callClaudeHeadless()` with a research prompt → saves findings to staging
4. At digest time (e.g., 20:00): loads all staged findings → prompts Claude to synthesize → sends digest to Telegram chat
5. Clears staging after digest is sent

## Architecture
- Scheduler runs in the same process as the Telegram bot
- `bot.start()` is non-blocking — scheduler starts after bot is initialized
- Crawls and digests are async — don't block the main bot
- Each job tracks `lastCrawl` and `lastDigest` timestamps to prevent duplicate runs
