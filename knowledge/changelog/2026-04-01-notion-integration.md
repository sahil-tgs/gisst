# 2026-04-01 — Notion Integration

## What was built
- **Notion client** (`src/notion/client.ts`) — Wrapper around @notionhq/client for database CRUD
- **Database schema** (`src/notion/schema.ts`) — Auto-creates "Research Findings" and "Daily Digests" databases on first boot
- **Sync pipeline** (`src/notion/sync.ts`) — Three sync functions:
  - `syncResearchToNotion()` — saves research responses (from SAVE_TO_NOTION markers)
  - `syncCrawlToNotion()` — saves individual crawl results from scheduler
  - `syncDigestToNotion()` — saves daily digest summaries
- **Auto-setup on boot** — If NOTION_API_KEY and NOTION_PAGE_ID are set, databases are created automatically

## How it connects
- Agent responses with `[SAVE_TO_NOTION: {...}]` markers → parsed in queue.ts → pushed to Research Findings database
- Scheduler crawls → saved to Research Findings with Type: "Crawl"
- Scheduler digests → saved to Daily Digests database + sent to Telegram
- Claude can read from Notion directly via its native WebFetch tools (no custom integration needed)

## Notion database structure
**Research Findings**: Title, Topic (select), Summary, Sources, Tags (multi_select), Date, Researcher, Session ID, Type (Research/Crawl/Digest)
**Daily Digests**: Title, Topic, Date, Finding Count, Schedule ID, Summary

## Config
```
NOTION_API_KEY=ntn_...
NOTION_PAGE_ID=33559250fbd880d4b639f26ba8d7af22
```
Database IDs are auto-generated and stored in `data/agents/notion-databases.json`
