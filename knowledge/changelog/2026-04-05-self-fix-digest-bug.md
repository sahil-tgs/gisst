# 2026-04-05 — Agent Self-Fix: Digest Timing Bug

## What happened
User told the bot via Telegram that scheduled digests weren't firing. The bot (Claude with --dangerously-skip-permissions) inspected its own codebase, diagnosed the bug, and fixed it autonomously.

## The bug
`isDigestDue()` in `src/scheduler/index.ts` used exact-minute matching:
```ts
if (now.getHours() !== hours || now.getMinutes() !== minutes) return false;
```
If the scheduler tick happened at 20:01 instead of exactly 20:00, the digest would never fire. Since the tick interval is 60s, there was only a 1-in-1 chance per day, and any delay meant a miss.

## Claude's fix
Changed to "past due today" logic:
```ts
const digestTotalMinutes = hours * 60 + minutes;
const currentTotalMinutes = now.getHours() * 60 + now.getMinutes();
if (currentTotalMinutes < digestTotalMinutes) return false;
```
Now the digest fires as soon as the current time is at or past the scheduled time, as long as it hasn't been sent today yet.

## Side effects
- Claude also likely detached the tmux session while running Bash commands to inspect the system, causing the bot to become an orphan process
- Crawls were working fine the entire time (staging data exists for April 1-5)
- Digests never fired due to the exact-minute bug

## Observation
This is the first instance of the agent self-modifying its own code to fix a bug. The fix is correct and should be committed.
