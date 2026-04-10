# 2026-04-04 (Sat): Second Backend, Queue, and the Telegram Channel

Long Saturday. Three things landed: the native Anthropic SDK backend, the
per-user async queue, and the aiogram bot. After today you can actually talk to
the agent.

## Anthropic SDK backend (`gisst.agent.runtime.api`)
A second `AgentRuntime` implementation that runs a native tool-use loop against
the Anthropic Messages API instead of shelling out to the CLI. Selected with
`AGENT_BACKEND=api`; needs `ANTHROPIC_API_KEY`.

The loop: send messages with the tool definitions, and while the model returns
`tool_use` blocks, execute the tools (web search / fetch), append `tool_result`
blocks, and re-invoke, up to `agent.max_turns` (default 12). `AgentResult.turns`
reports how many round-trips it took. Because the SDK has no opaque session file,
we keep the running message list keyed by the session id ourselves.

Why two backends: the CLI path is cheap and tool-rich but spawns a process per
turn and depends on a logged-in CLI; the API path is faster, fully programmatic,
and deployable without an interactive login, at metered cost. Same `AgentRuntime`
Protocol, so the composition root picks one from config and nothing downstream
notices.

## Per-user async queue (`gisst.agent.queue`)
The agent must never run two concurrent turns against the *same* Claude session
(session resume would corrupt). The queue gives each `user_id` its own
`asyncio.Queue` + worker task: strictly sequential per user, fully parallel
across users.

The worker is the real pipeline: pull a message, resolve the session id from
`SessionRepository`, build the prompt, call `runtime.run(...)`, run the result
through `parse_notion_marker`, persist any finding via `ResearchRepository`,
write the (possibly new) session id back, and hand the clean text to the
`Notifier` for delivery. The Notion push itself gets wired in tomorrow; today the
hook exists and records to the DB.

## Notifier protocol (`gisst.core.notifier`)
`Notifier` is a one-method Protocol: `async send_text(chat_id, text)`. Producers
of outbound content (the queue, the digest pipeline) depend on this, not on
Telegram. Keeps the dependency graph acyclic: `queue -> core.Notifier`, never
`queue -> telegram`. `split_message` (in `gisst.core.text`) chunks long bodies
under `TELEGRAM_SPLIT_TARGET` so implementations can honour channel limits.

## aiogram v3 bot (`gisst.telegram`)
The first real channel.
- `client.py`: builds the `Bot` + `Dispatcher`, registers routers, runs
  long-polling (no webhook infra needed for the prototype).
- Command router: `/start`, `/help`, `/schedule ...`, `/jobs`, status, etc.
- Message router: routes free-form text into the queue, honouring the profile's
  trigger mode (all / mention / command).
- Group gating: in groups the bot only responds in chats present in the
  `GroupRepository` allowlist; an admin registers a group explicitly. DMs are
  always allowed.
- `TelegramNotifier`: the concrete `Notifier`, splits long replies and best-effort
  delivers each chunk (a failed chunk never aborts the rest).
