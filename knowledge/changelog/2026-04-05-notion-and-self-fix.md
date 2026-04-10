# 2026-04-05 (Sun): Notion Knowledge Base, and an Agent Self-Fix

## Notion integration (`gisst.notion`)
The agent now keeps a real knowledge base. Async, no blocking HTTP on the event
loop.

- `client.py`: thin async wrapper over the Notion REST API (`httpx`), pinned to
  API version `2022-06-28` from config. Handles pages, database creation, and
  block appends; `NOTION_TEXT_LIMIT` (2000 chars per rich-text object) is
  respected when chunking long summaries.
- `schema.py`: on first boot, if `NOTION_API_KEY` + `NOTION_PAGE_ID` are set and
  no DB ids are stored yet, auto-provisions two databases under the parent page:
  **Research Findings** and **Daily Digests**, with the right properties
  (Title, Topic, Type select using `NOTION_TYPE_RESEARCH/CRAWL/DIGEST`, Tags,
  Sources, Schedule ID, Created). The created database ids are persisted so the
  next boot skips provisioning.
- `sync.py`: maps a `ResearchFinding` / `CrawlFinding` / digest into Notion
  pages: a page per finding with key-findings and sources as child blocks, a page
  per daily digest. Returns the created Notion page id so the repository row can
  store it (round-trips back to the dashboard).

### Wired into the pipeline
The queue worker's Notion hook (stubbed yesterday) is now live: after
`parse_notion_marker` yields a finding, the worker calls `ResearchRepository`
*and* `NotionSync`, stashing the returned `notion_page_id` on the row. Notion is
optional: if disabled, everything still works, findings just live in SQLite
only.

## Agent self-fix: digest timing bug
While testing scheduled digests over the weekend, a user reported via Telegram
that digests weren't firing. The agent (running with
`--dangerously-skip-permissions`) inspected its own source, diagnosed the bug,
and proposed the fix. Worth recording because it is the first time the agent
modified its own behaviour.

The defect: the digest-due check used exact-minute matching (fire only when the
current hour *and* minute equal the scheduled time). With a 60s scheduler tick,
any tick that landed at 20:01 instead of 20:00 missed the window entirely, so
digests almost never fired. Crawls were fine the whole time: staging had data,
nothing was delivering it.

The agent's diagnosis was correct. The actual code change (exact-minute ->
at-or-past-due) is applied and documented in the day-7 changelog alongside the
Watchout pipeline it belongs to, so the fix lands with its surrounding context
rather than as a stray patch.
