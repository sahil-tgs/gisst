# Current State

## Status: Prototype Live on VM (2026-04-01)

### Completed
- [x] Agent core — Claude CLI spawner, session management, two-layer prompt system
- [x] Telegram integration — grammy bot, group management, @mention/command triggers
- [x] Watchout Protocol — scheduler, crawl/digest pipeline, Telegram commands
- [x] Notion integration — auto-setup databases, sync research/crawl/digest
- [x] VM deployment — running on scraper-vm in tmux

### Live on VM
- Bot: @rankly_agent_bot (tmux session: gisst)
- Notion: Connected to "Knowledge Base" page with Research Findings + Daily Digests databases
- Scheduler: Running, checks every 60s for due crawls/digests

### Up Next
- [ ] Agent configuration via Telegram (!configure commands)
- [ ] Notion knowledge base reading (!kb command)
- [ ] Improve digest quality — have Claude reference past Notion entries
- [ ] WhatsApp integration (when Facebook appeal resolves or via spare number + Evolution API)
- [ ] User profiles and conversation metadata
- [ ] Multiple agent support (different configs per group)
