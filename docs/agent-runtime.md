# Agent runtime

The agent runtime is the layer that actually "talks to Claude". It is deliberately
narrow: it takes a prompt plus a system prompt plus an optional session handle, and
returns the raw text and the resolved session id. Everything else (marker parsing,
persistence, Notion sync, message splitting) happens *above* the runtime so backends stay
focused on a single job.

## The runtime contract

Every backend implements one Protocol, defined in `gisst.agent.runtime.base`:

```python
@runtime_checkable
class AgentRuntime(Protocol):
    name: str

    async def run(self, request: AgentRequest) -> AgentResult:
        """Execute one agent turn and return the raw text result."""
        ...
```

Because both backends satisfy the same interface and return the same result type, the
queue and the scheduler are written once and never branch on which backend is active.

### `AgentRequest`

Everything a backend needs for one turn:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `prompt` | `str` | required | The user (or crawl / digest) message for this turn. |
| `system_prompt` | `str` | required | The rendered two-layer system prompt. |
| `session_id` | `str \| None` | `None` | The session to resume, if any. |
| `headless` | `bool` | `False` | When `True`, this is a background Watchout job; no session is created or persisted. |
| `metadata` | `dict[str, str]` | `{}` | Free-form tags (job id, chat id, finding type) for logging and routing. |

### `AgentResult`

The outcome of one turn:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `text` | `str` | required | The raw assistant text (still contains any save marker). |
| `session_id` | `str \| None` | `None` | The resolved session id to persist for next time. |
| `backend` | `str` | `""` | Which backend produced this (`cli` / `api`), for observability. |
| `turns` | `int` | `1` | How many tool-use turns it took. |

A backend raises `RuntimeError_` (from the same module) when it cannot produce a usable
response. The queue catches it and replies with a graceful error instead of crashing.

## The two backends

`build_runtime` selects one based on `AGENT_BACKEND` (see
[configuration.md](configuration.md#agent-runtime-settingsagent)).

### `cli` - Claude Code CLI

The default. It shells out to the Claude Code CLI in headless mode:

```
claude -p "<prompt>" --resume <session_id> --append-system-prompt "<system_prompt>" ...
```

Why this is the primary path:

- **Batteries included.** The CLI brings native WebSearch and WebFetch, file tools, and
  its own tool-permission handling, so research "just works" without re-implementing
  tools.
- **Session persistence is native.** The CLI owns the conversation history. We pass
  `--resume <session_id>` to continue, and parse the session id back out of the result so
  the next turn resumes the same conversation. The first call has no session id; the CLI
  creates one and we store it.
- **Operationally simple on a VM** where the CLI is installed and logged in. Runs under
  `--dangerously-skip-permissions` so it never blocks waiting for an interactive tool
  approval.

The runtime enforces `AGENT_TIMEOUT` on the subprocess and uses `CLAUDE_MODEL` for the
model. It runs in `settings.work_dir`.

### `api` - Anthropic SDK

For environments where the CLI is not installed or not logged in (containers, serverless,
CI). It runs a native Anthropic SDK tool-use loop:

- It calls the Messages API with `CLAUDE_MODEL`, advertises its own WebSearch / WebFetch
  tool definitions, and loops, feeding tool results back, until the model returns a final
  answer or it hits `AGENT_MAX_TURNS`. `turns` on the result reflects how many passes it
  took.
- **Sessions are emulated.** The SDK is stateless per call, so the backend reconstructs
  context from stored history keyed by the session id rather than relying on a
  CLI-managed session.
- Requires `ANTHROPIC_API_KEY`.

Switching backends is a one-line env change. No other code moves.

## Sessions and `--resume`

Continuity is what makes the agent feel like a persistent researcher rather than a
stateless Q&A bot.

- Each user maps to one resumable session id, persisted through
  `Repositories.sessions` (`get(user_id)`, `set(user_id, session_id)`, `delete(user_id)`),
  backed by the `sessions` table (one row per user).
- On each turn the queue reads the stored session id, puts it on the `AgentRequest`, and
  after the run writes back `result.session_id`. The CLI backend uses `--resume` to
  continue that exact conversation; the SDK backend replays the stored history.
- **Headless Watchout runs set `headless=True`**, so they never create or persist a
  session. Background crawls and digests must not pollute a user's interactive thread.
- Clearing a user's session (for example a `/reset` style command) calls
  `sessions.delete`, and the next turn starts a fresh conversation.

## The two-layer prompt

The system prompt handed to a backend is composed of two layers, so the agent's
personality is configurable without forking the core instructions:

1. **Base layer (DNA).** Hardcoded instructions that define the research methodology:
   search broadly, cross-reference, cite every factual claim, format for chat, and emit
   the `[SAVE_TO_NOTION: {...}]` marker when a result is worth keeping. This layer is the
   same for every deployment and never changes at runtime.
2. **User layer (persona).** Rendered from the active `AgentProfile`
   (`gisst.models.agent`). It injects the configured `identity` (name, `Tone`, language,
   emoji style), `research` settings (depth, topics, source preferences, citation
   style), and `interaction` settings (response length, follow-up behaviour, auto-save,
   trigger mode).

For Watchout runs there are two additional, dedicated prompts layered on the same base:
a **crawl prompt** (find what is new on this topic since the lookback window, return
structured findings) and a **digest prompt** (synthesise today's staged findings into one
briefing). See [watchout-protocol.md](watchout-protocol.md).

## The `SAVE_TO_NOTION` marker contract

This is the bridge between free-form agent text and structured, persistable knowledge.
When the agent decides a result is worth keeping, it appends a marker to its response:

```
[SAVE_TO_NOTION: { ...JSON... }]
```

The tag is `NOTION_MARKER_TAG` (`[SAVE_TO_NOTION:`) from `gisst.constants`. Parsing lives
in `gisst.agent.markers.parse_notion_marker(text) -> ParsedResponse`:

- It finds the tag, then does a **balanced-brace scan** to extract the JSON object (a
  regex would break because the summary text can itself contain braces).
- It validates the JSON into a `ResearchFinding`. Validation is lenient: it accepts the
  agent's camelCase (`keyFindings`) as well as snake_case, and coerces bare URL strings
  in `sources` into `{title, url}` objects.
- It strips the entire marker from the text so the user never sees it.
- The result is `ParsedResponse(clean_text, finding)`. If there is no marker, or the JSON
  is malformed, `finding` is `None`, a warning is logged, and `clean_text` is the
  original text. The user still gets a reply; nothing crashes.

### Finding schema (`ResearchFinding`)

| Field | Type | Notes |
| --- | --- | --- |
| `title` | `str` | Required. |
| `topic` | `str` | Optional, defaults to `""`. |
| `summary` | `str` | Optional, defaults to `""`. |
| `key_findings` | `list[str]` | Accepts `keyFindings`; `None` coerced to `[]`. |
| `sources` | `list[ResearchSource]` | Bare URL strings are coerced to `{title, url}`. |
| `tags` | `list[str]` | `None` coerced to `[]`. |

### Example

A response the agent might produce:

```
Here's where the EU AI Act enforcement stands: the first compliance deadlines for
prohibited-use systems landed in early 2025, with the AI Office now staffing up to
oversee general-purpose model obligations that phase in through 2025 and 2026.

[SAVE_TO_NOTION: {
  "title": "EU AI Act enforcement timeline",
  "topic": "AI regulation",
  "summary": "Phased enforcement: prohibited-use bans first, GPAI obligations next, full applicability later.",
  "keyFindings": [
    "Prohibited-use provisions apply first in the rollout",
    "The AI Office oversees general-purpose model obligations",
    "Remaining obligations phase in across 2025-2026"
  ],
  "sources": [
    {"title": "European Commission - AI Act", "url": "https://digital-strategy.ec.europa.eu/en/policies/ai-act"},
    "https://artificialintelligenceact.eu/"
  ],
  "tags": ["eu-ai-act", "regulation", "enforcement"]
}]
```

After `parse_notion_marker`:

- **`clean_text`** is just the briefing paragraph (the marker block removed and trimmed).
- **`finding`** is a validated `ResearchFinding`. The second source, a bare URL string,
  is coerced into `ResearchSource(title="https://...", url="https://...")`.

The queue then delivers `clean_text` to Telegram, calls
`Repositories.research.record_finding(finding, researcher=...)`, and (when Notion is
enabled) syncs the finding to the Research Findings database, storing the returned
`notion_page_id`.
