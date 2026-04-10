# Watchout Protocol: Scheduled Research

The Watchout Protocol is Gisst's self-driving research mode. A user defines a
topic to watch; the agent crawls it on a cadence throughout the day, accumulates
findings, and delivers one synthesised digest at a chosen time. Full data lands
in Notion; the summary goes to the chat.

## Concept
Conversational research is pull (the user asks). Watchout is push: the agent
keeps watching a topic and surfaces what changed, on a schedule, without being
prompted each time.

## The job
A job is a `ScheduleJobState` (see `gisst.models.schedule`):

| Field | Meaning |
| --- | --- |
| `topic` | What to watch ("Agentic commerce") |
| `keywords` | Search terms that focus each crawl |
| `cadence` | How often to crawl (e.g. `every 4h`) |
| `lookback_window` | How far back a crawl considers ("24h") |
| `digest_time` + `digest_timezone` | When the daily briefing fires, in whose clock |
| `platform_priority` | Domains to prefer (reuters.com, arxiv.org, ...) |
| `active` | Pause without deleting |
| `chat_id` / `created_by` | Where the digest is delivered, and by whom |
| `last_crawl` / `last_digest` | Run bookkeeping for due-checks and idempotency |

## Pipeline
```
Scheduler tick (every scheduler.tick_seconds)
   |
   |-- crawl due? (cadence vs. last_crawl)
   |      -> headless agent run (Watchout crawl prompt, keywords + lookback)
   |      -> Claude returns JSON array of CrawlFinding
   |      -> StagingRepository.add(job_id, content)  [per (job_id, day)]
   |      -> jobs.touch(job_id, "last_crawl")
   |
   '-- digest due? (now at-or-past digest_time in tz, and last_digest not today)
          -> load StagingRepository.list_for_day(job_id)
          -> headless agent run (Watchout digest prompt, all staged findings)
          -> Claude synthesises one briefing
          -> Notifier.send_text(chat_id, summary)   (Telegram)
          -> NotionSync.write_digest(...)           (digest page)
          -> ResearchRepository.record_digest(...)
          -> jobs.touch(job_id, "last_digest"); staging.clear(job_id)
```

### Crawls are headless
Crawl and digest runs use `AgentRequest(headless=True)`: no Claude session is
created or persisted (they are not part of any user's conversation), and a
distinct prompt (Watchout crawl / digest) is used instead of the conversational
one. They share the same `AgentRuntime` as chat: same backend, different prompt.

### Staging
Each crawl result is appended to staging keyed by `(job_id, day)`.
`StagingRepository.add` returns the running count for the day. Crawls never
deliver to the user; staging is just the buffer the digest reads. After a digest
fires, `staging.clear(job_id)` wipes the day so the next day starts clean.

## Digest timing (the fixed logic)
The digest due-check is **at-or-past due, once per day**, not exact-minute:

1. Resolve `digest_time` in the job's `digest_timezone` to a wall-clock instant
   for today.
2. Fire when *now is at or past* that instant **and** `last_digest` is not
   already today.

This is robust to a late scheduler tick (a tick at 20:01 still delivers) and
idempotent on restart (the `last_digest`-is-today guard means catch-up fires
exactly once). The earlier exact-minute check silently dropped digests whenever a
tick missed the precise minute.

## Notion layout
- One page per daily digest in the **Daily Digests** database, with the
  synthesised briefing and a `Schedule ID` back-reference to the job.
- Individual crawl findings can be written to **Research Findings** with source,
  timestamp, and relevance as child blocks.
- `notion_page_id` is round-tripped onto the DB row so the dashboard can deep-link.

## Telegram control surface
- `/schedule "Agentic commerce" daily 20:00`: quick setup
- `/jobs`: list this chat's jobs (short ids)
- pause/resume a job (`toggle`)
- remove a job
Short-id lookups go through `ScheduleJobRepository.find_by_prefix`, so users
never paste full UUIDs.
