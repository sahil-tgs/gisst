# 2026-04-01 — Switched from WhatsApp to Telegram

## Why
- WhatsApp Cloud API: User's Facebook account suspended, blocking setup
- Baileys (all versions v6.x, v7.x, GitHub master): Broken — WhatsApp protocol updated, all versions fail with 405/428 errors. QR code never generates.
- whatsapp-web.js: Would require Chromium, heavy for a VM
- Twilio WhatsApp: DM-only, no group chat support
- WhatsApp Business API: No group chat support at all

## What was built
- **grammy-based Telegram bot** (`src/telegram/client.ts`) — polling-based, no webhooks needed
- **Group management**: `/register` command to activate bot in a group
- **Trigger system**: Bot responds to @mentions, !commands, direct replies, and "Scout"/"Gisst" keyword mentions
- **Group privacy**: Disabled via BotFather so bot can see all group messages
- **Pairing code auth**: Originally attempted for WhatsApp, not needed for Telegram

## Telegram commands
- `/start` — welcome message
- `/register` — activate in group
- `/schedule <topic>` — create scheduled research job
- `/schedules` — list active jobs
- `/pause <id>` — toggle job
- `/remove <id>` — delete job

## Key decision
Telegram bots are first-class citizens with their own identity — exactly what was needed. WhatsApp was never designed for bots and every solution is either broken or limited.

## Bot details
- Token: set via TELEGRAM_BOT_TOKEN env var
- Username: @rankly_agent_bot
- Name: Scout
