# Scheduled Research & Cron System

## Concept
The agent can self-schedule recurring research jobs. It crawls throughout the day on a cadence, accumulates findings, and delivers a digest at the user's preferred time. Full research data goes to Notion, summary goes to WhatsApp.

## How it works

### Flow
1. User tells agent: "Track agentic commerce news, daily digest at 8pm"
2. Agent (or our system) creates a cron entry in the config
3. Throughout the day, cron fires background research jobs (e.g., every 4 hours)
4. Each job: claude -p "search for latest on {topic}" → results saved to a staging file/buffer
5. At digest time: claude -p "summarize today's findings on {topic}" → WhatsApp summary + full Notion page

### Cron runs are headless
- No WhatsApp message triggers these — they're self-initiated by the system
- Uses the same claude -p pipeline but with a research-specific prompt
- Results accumulate in a local staging area (JSON file per topic per day)
- Digest prompt gets all staged results as context, synthesizes into one briefing

### User config additions
```json
{
  "schedules": [
    {
      "id": "uuid",
      "topic": "Agentic Commerce",
      "keywords": ["agentic commerce", "AI shopping", "autonomous purchasing"],
      "cadence": "every 4 hours",
      "digestTime": "20:00",
      "digestTimezone": "Asia/Kolkata",
      "sources": ["news", "twitter", "reddit", "arxiv"],
      "platformPriority": ["reuters.com", "techcrunch.com", "arxiv.org"],
      "lookbackWindow": "48h",
      "active": true
    }
  ],
  "globalScheduleSettings": {
    "maxJobsPerDay": 20,
    "quietHours": { "start": "23:00", "end": "06:00" },
    "defaultDigestTime": "20:00",
    "defaultTimezone": "Asia/Kolkata"
  }
}
```

### Commands (via WhatsApp)
- `!schedule "Agentic Commerce" daily 8pm` — quick setup
- `!schedule list` — show all active schedules
- `!schedule pause <id>` — pause a schedule
- `!schedule remove <id>` — delete a schedule
- Agent can also self-suggest: "Want me to track this topic daily?"

### Implementation approach
- Bun has no native cron — use `setInterval` or a lightweight scheduler
- Each interval tick checks: any jobs due? → spawn claude -p for background research
- Staging area: `data/staging/{topic}/{date}.json` — array of findings per crawl
- At digest time: load all staged findings → prompt Claude to synthesize → send WhatsApp + push Notion

### Notion structure for scheduled research
- One Notion page per digest (daily summary)
- Child blocks for each individual finding with source, timestamp, relevance
- Database property: `Schedule ID` to link findings back to the schedule config
