# 2026-04-03: Agent Runtime and Prompt Engine

The agent itself. Defined the runtime contract, shipped the first backend
(Claude Code CLI), built the two-layer prompt engine, and wrote the
`SAVE_TO_NOTION` marker parser.

## Runtime protocol (`gisst.agent.runtime.base`)
A backend is anything that satisfies the `AgentRuntime` Protocol: a `name` and
`async run(AgentRequest) -> AgentResult`.

- `AgentRequest(prompt, system_prompt, session_id=None, headless=False, metadata={})`.
  `headless=True` marks a background Watchout crawl/digest, where no session is
  created or persisted.
- `AgentResult(text, session_id=None, backend="", turns=1)`.
- `RuntimeError_` is the one failure type backends raise.

Crucially, marker parsing and Notion sync happen *above* the runtime, in the
queue/pipeline. Backends only have one job: talk to Claude and return raw text.
That keeps them swappable.

## CLI backend (`gisst.agent.runtime.cli`)
Shells out to the Claude Code CLI with `asyncio.create_subprocess_exec`. Uses
`claude -p` for headless prompting, `--output-format json` to read back the
result text and the resolved `session_id`, `--dangerously-skip-permissions` so
WebSearch / WebFetch / Bash run unattended, and `--resume <session_id>` to
continue an existing conversation. On the first turn there is no session id;
Claude creates one and we read it out of the JSON envelope, then hand it to the
`SessionRepository`. Honors `agent.timeout_seconds`; non-zero exit raises
`RuntimeError_`.

This is the cheap path: it rides the user's Claude Code plan and gets all the
built-in tools for free. The trade-off is process-spawn overhead per turn, fine
at prototype scale.

## Prompt engine (`gisst.agent.prompt`)
Two layers, composed at call time:
1. **Base layer**: hardcoded "DNA": who the agent is, how it researches, the
   exact `[SAVE_TO_NOTION: {...}]` output contract with a JSON schema example.
2. **User layer**: rendered from the active `AgentProfile`: name, tone,
   research depth, source preferences, citation style, response length, trigger
   mode. Changing the profile changes behaviour without touching the base.

Separate prompt builders for conversational turns vs. the headless Watchout
crawl and digest prompts (those come into play on day 7).

## Marker parser (`gisst.agent.markers`)
`parse_notion_marker(text) -> ParsedResponse(clean_text, finding)`.

The agent embeds a JSON object inside `[SAVE_TO_NOTION: {...}]`. A regex won't do
because the summary text can itself contain braces, so the extractor does a
balanced-brace scan from the tag, slices out the JSON, validates it into a
`ResearchFinding`, and strips the whole marker from the user-facing text. Invalid
JSON logs a warning and returns the text untouched (the user still gets their
answer; we just don't save).
