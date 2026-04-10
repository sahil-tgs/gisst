# Open Questions

Honest unknowns. Recorded here instead of guessed at in code.

## Agent runtime
- Which backend is the default we recommend? CLI is cheap and tool-rich but needs
  an interactive login on the VM; API is clean to deploy but metered. Right now
  `AGENT_BACKEND` defaults to `cli`: is that the right default for a portfolio
  repo someone clones, given they may not have a Claude Code login?
- The API backend re-implements web search/fetch as tools. Do we keep our own
  tool implementations, or lean on a hosted tool layer so both backends share the
  exact same tool behaviour?
- Per-turn cost on the API path is unmeasured. Need real numbers before we'd ever
  put it on a busy group.

## Profiles and multi-tenancy
- Profile scope: per-chat, per-group, or per-user? Groups argue for per-group;
  DMs argue for per-user. Probably both, with a resolution order: undecided.
- When a profile changes mid-conversation, do we reset the Claude session or let
  the new persona apply on the next turn only?

## Watchout Protocol
- Cadence is a free-text string today (`every 4h`). Move to a real cron
  expression, or keep the friendly grammar and parse it? Cron is precise but
  user-hostile in chat.
- Crawl dedup: across a day, the same story can surface in multiple crawls. Do we
  dedup at staging time (by URL/headline) or let the digest prompt handle it?
- Lookback vs. cadence overlap means findings get re-seen. Acceptable noise, or
  worth a "seen" set per job?

## Storage and scale
- When do we actually need Postgres? SQLite WAL is fine for one VM. The trigger
  is probably multiple app instances (webhooks) sharing state, not row count.
- The JSON-in-text list columns (keywords, sources, tags) are unqueryable. Worth
  normalising now, or only once a feature needs to filter on them?

## Channels
- Telegram group gating is an explicit allowlist. For Discord/Slack, is allowlist
  still right, or do those platforms' own permission models replace it?
- Do we want a single unified inbox abstraction over channels, or keep each
  channel's adapter thin and let the queue be the only shared point?

## Operability
- Where do agent errors surface? Right now: logs + best-effort chat delivery.
  Should failures also post to an admin channel or the dashboard as alerts?
- Notion is optional and best-effort. If a Notion write fails after the DB row is
  written, do we retry, or accept the row is the source of truth and Notion is a
  mirror?
