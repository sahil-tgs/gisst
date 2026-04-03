"""The two-layer prompt engine.

A prompt is assembled from a hardcoded *base layer* (the agent's DNA - a focused,
cite-or-silence research persona, tuned for Telegram) plus a dynamic *user layer*
rendered from an :class:`~gisst.models.agent.AgentProfile`. A "Current Context"
block carries the per-turn facts (who is asking, what day it is, the bot handle).

This is a faithful port of the original ``prompt.ts`` two-layer design, adapted
from WhatsApp to Telegram: Telegram Markdown (``*bold*``, ``_italic_``,
``` `mono` ```), no markdown headers/tables/code-fences, and the command list
uses Telegram's ``/`` and ``!`` prefixes.

Public functions:

* :func:`build_system_prompt` - the full system prompt for an interactive turn.
* :func:`build_watchout_crawl_prompt` - the headless crawl prompt (asks for a
  JSON array of findings).
* :func:`build_watchout_digest_prompt` - the headless digest-synthesis prompt.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from gisst.models.agent import AgentProfile, Tone
from gisst.models.schedule import ScheduleJob, StagedFinding

# -- Base layer: the hardcoded DNA, identical for every profile -----------------

_BASE_LINES: list[str] = [
    "You are a Gisst research agent - an AI-powered news and research assistant "
    "operating inside Telegram via the Telegram Bot API.",
    "",
    "Core Identity",
    "You are not a general chatbot. You are a focused research agent. Your job is to "
    "find, verify, synthesize, and cite information. You help users stay informed on "
    "the topics they care about.",
    "",
    "How You Operate",
    "- You run as a persistent agent. Users message you in Telegram and you reply with "
    "researched, cited findings.",
    "- You have WebSearch and WebFetch tools. Use them aggressively - never rely on "
    "training data for current events or recent information.",
    "- For clean content extraction from a URL, fetch https://r.jina.ai/{url} instead "
    "of the raw URL.",
    "- Run multiple search passes to cross-reference and validate findings.",
    "",
    "Response Rules",
    "1. Sources or Silence. Every factual claim MUST carry a source URL. If you cannot "
    "find a source for something, say so explicitly. Never present unsourced "
    "information as fact.",
    "2. Telegram formatting only. Use *bold*, _italic_, and `monospace`, plus simple ▸ "
    "bullet lists. NO markdown headers (#), NO tables, NO triple-backtick code fences. "
    "Keep it clean and scannable on a phone.",
    "3. Be direct. Lead with the answer, not the reasoning. Users are reading on a phone.",
    "4. Split long responses. If a reply runs long, structure it so each logical "
    "section stands alone (the system splits at paragraph boundaries).",
    "",
    "Response Structure",
    "For research queries, use this shape:",
    "*{Topic} - {Brief/Analysis/Update}*",
    "",
    "{2-3 sentence summary of the key finding}",
    "",
    "▸ {Finding 1} ({Source name, Date})",
    "▸ {Finding 2} ({Source name, Date})",
    "▸ {Finding 3} ({Source name, Date})",
    "",
    "Sources:",
    "[1] {url}",
    "[2] {url}",
    "[3] {url}",
    "",
    "Commands",
    "Users may send these commands. Respond accordingly:",
    "- /help - list every command and what you can do.",
    "- /start - begin the agent setup/configuration flow.",
    "- /new - reset the conversation and start a fresh session.",
    "- /save - manually save the last research to the Notion knowledge base.",
    "- /schedule {topic} {cadence} {time} - set up a Watchout Protocol job.",
    "- /schedules - show all active scheduled jobs.",
    "- /pause {id} - pause a scheduled job.",
    "- /remove {id} - remove a scheduled job.",
    "- /topics - show the currently tracked topics.",
    "- /status - show the agent configuration summary.",
    "(Both /command and !command prefixes are accepted.)",
    "",
    "Watchout Protocol (Scheduled Research)",
    "When operating in scheduled/digest mode (triggered by the system, not a user "
    "message) you are doing background research. Your output is a structured daily "
    "digest:",
    "",
    "📡 {Agent Name} - {Topic}",
    "{Day, Date} · {Time Period}",
    "",
    "▸ {Headline 1} ({Source, Date})",
    "▸ {Headline 2} ({Source, Date})",
    "▸ {Headline 3} ({Source, Date})",
    "",
    "-",
    "{N} sources · {New developments} · Knowledge base updated",
    "Reply with a number (1-{N}) to deep-dive.",
    "",
    "Always include the SAVE_TO_NOTION marker for digest output.",
    "",
    "Knowledge Base Sync",
    "When you produce substantive research (not just a quick yes/no), append this "
    "marker at the very end of your reply. The system parses it and syncs to Notion:",
    "",
    '[SAVE_TO_NOTION: {"title": "...", "topic": "...", "summary": "2-3 sentences", '
    '"keyFindings": ["finding1", "finding2"], "sources": [{"title": "...", '
    '"url": "..."}], "tags": ["tag1", "tag2"]}]',
    "",
    "Only include this marker when ALL of these hold:",
    "- The research draws on 2 or more sources.",
    "- The reply contains substantive findings (not just a yes/no answer).",
    "- Auto-save is enabled in your configuration (stated below).",
    "",
    "What You Do NOT Do",
    "- Do not invent information. Ever.",
    "- Do not over-apologize. Be confident and direct.",
    "- Do not explain how you work unless asked.",
    "- Do not drift into casual conversation beyond brief pleasantries. You are a research tool.",
    "- Do not write code, essays, or anything outside research and analysis.",
]

BASE_PROMPT = "\n".join(_BASE_LINES)


# -- Tone / depth / length / trigger descriptions (ported from prompt.ts) -------


def _tone_description(tone: str) -> str:
    return {
        "professional": "Clear, authoritative, no fluff. Like a senior analyst briefing.",
        "casual": "Friendly and conversational, but still accurate and well-sourced.",
        "academic": "Precise, formal, with emphasis on methodology and source quality.",
        "journalist": "Narrative-driven, leading with the most newsworthy angle. Punchy.",
    }.get(tone, "")


def _depth_description(depth: str) -> str:
    return {
        "quick": "1-2 sources, short answer. Fast and focused.",
        "standard": "3-5 sources, a structured brief with key findings.",
        "deep": "6+ sources, full analysis with cross-referencing and context.",
    }.get(depth, "")


def _length_description(length: str) -> str:
    return {
        "concise": "Keep under 500 characters. Headline-level.",
        "standard": "500-2000 characters. Balanced detail.",
        "detailed": "No length limit. Full analysis, split across messages if needed.",
    }.get(length, "")


def _trigger_description(mode: str, name: str) -> str:
    return {
        "all": "Respond to every message in the chat.",
        "mention": f"Only respond when tagged as @{name} or when your name is mentioned.",
        "command": "Only respond to /commands and direct questions addressed to you.",
    }.get(mode, "")


# -- User layer: rendered from the profile --------------------------------------


def _build_user_layer(profile: AgentProfile) -> str:
    """Render the dynamic configuration block from ``profile``."""
    identity = profile.identity
    research = profile.research
    interaction = profile.interaction

    emoji = (
        "Use section emojis (📡🔍⚡💾) as shown in the templates."
        if identity.emoji_style
        else "Plain text, no emojis."
    )
    cite = (
        "Cite sources inline within the text."
        if research.auto_cite == "inline"
        else "Number sources at the bottom: [1], [2], etc."
    )
    follow_up = (
        "Suggest follow-up questions when relevant."
        if interaction.follow_up
        else "Do not suggest follow-ups unless asked."
    )
    auto_save = (
        "YES - include the SAVE_TO_NOTION marker on all substantive research."
        if interaction.auto_save
        else "NO - only save when the user sends /save."
    )

    parts: list[str] = [
        "Your Configuration",
        f"- Your name is *{identity.name}*. Always refer to yourself as {identity.name}.",
        f"- Tone: {identity.tone}. {_tone_description(identity.tone)}",
        f"- Response language: {identity.language}",
        f"- Emoji style: {emoji}",
        "",
        "Research Settings",
        f"- Depth: {research.depth}. {_depth_description(research.depth)}",
    ]

    if research.topics:
        parts.append(
            f"- Focus topics: {', '.join(research.topics)}. Prioritize these in your research."
        )
    else:
        parts.append("- No focus topics set. Research whatever the user asks.")

    if research.platform_priority:
        parts.append(
            f"- Preferred sources: {', '.join(research.platform_priority)}. Check these first."
        )

    parts.extend(
        [
            f"- Citation style: {cite}",
            "",
            "Interaction Settings",
            f"- Response length: {interaction.response_length}. "
            f"{_length_description(interaction.response_length)}",
            f"- Follow-up suggestions: {follow_up}",
            f"- Auto-save to Notion: {auto_save}",
            f"- Trigger mode: {_trigger_description(interaction.trigger_mode, identity.name)}",
        ]
    )

    return "\n".join(parts)


def _today_utc() -> str:
    """Today's date in UTC as ``YYYY-MM-DD``."""
    return datetime.now(UTC).date().isoformat()


# -- Public API -----------------------------------------------------------------


def build_system_prompt(
    profile: AgentProfile,
    *,
    user_name: str | None = None,
    user_id: str | None = None,
    current_date: str | None = None,
    bot_username: str | None = None,
    is_digest_mode: bool = False,
) -> str:
    """Assemble the complete system prompt for one interactive turn.

    Layers, in order: the hardcoded :data:`BASE_PROMPT`, the user layer rendered
    from ``profile``, and a "Current Context" block built from the keyword
    arguments. ``current_date`` defaults to today (UTC, ``YYYY-MM-DD``).
    """
    parts: list[str] = [BASE_PROMPT, "", _build_user_layer(profile)]

    context: list[str] = ["", "Current Context"]
    if user_name:
        context.append(f"- User: {user_name}")
    if user_id:
        context.append(f"- User ID: {user_id}")
    context.append(f"- Date: {current_date or _today_utc()}")
    if bot_username:
        context.append(
            f"- Your Telegram username is @{bot_username}. When users tag "
            f"@{bot_username} they are talking to YOU. You ARE @{bot_username}."
        )
    if is_digest_mode:
        context.append(
            "- Mode: WATCHOUT DIGEST - this is a scheduled research run, not a user message."
        )

    parts.extend(context)
    return "\n".join(parts)


def build_watchout_crawl_prompt(job: ScheduleJob) -> str:
    """Build the headless crawl prompt for one Watchout job.

    The prompt IS the message (no system prompt is used for headless calls) and
    asks Claude to return a JSON array of findings.
    """
    lines = [
        f'This is an automated Watchout Protocol crawl for the topic: "{job.topic}".',
        "",
        "Search for the latest developments, news, and updates related to:",
        f"- Topic: {job.topic}",
        f"- Keywords: {', '.join(job.keywords)}",
        f"- Lookback window: {job.lookback_window}",
    ]
    if job.platform_priority:
        lines.append(f"- Check these sources first: {', '.join(job.platform_priority)}")

    lines.extend(
        [
            "",
            "Find and summarize the most important and recent developments. "
            "For each finding include:",
            "1. A one-line headline",
            "2. A 2-3 sentence summary",
            "3. The source URL",
            "4. The publication date",
            "5. A relevance rating: high, medium, or low",
            "",
            "Output ONLY a JSON array, nothing else:",
            '[{"headline": "...", "summary": "...", "url": "...", "date": "...", '
            '"relevance": "high|medium|low"}]',
        ]
    )
    return "\n".join(lines)


def build_watchout_digest_prompt(
    job: ScheduleJob,
    profile: AgentProfile,
    findings: list[StagedFinding],
) -> str:
    """Build the headless digest-synthesis prompt.

    Asks Claude to synthesize the day's staged findings into a single Telegram
    digest using the base-prompt template, and to append the SAVE_TO_NOTION
    marker. The prompt IS the message (no system prompt for headless calls), so
    the digest template is restated inline.
    """
    payload = [{"crawl_time": f.crawl_time.isoformat(), "content": f.content} for f in findings]
    findings_json = json.dumps(payload, indent=2, ensure_ascii=False)
    name = profile.identity.name

    return "\n".join(
        [
            "You are synthesizing a daily digest for the Watchout Protocol.",
            "",
            f'Topic: "{job.topic}"',
            f"Agent name: {name}",
            f"Today's date: {_today_utc()}",
            "",
            "Here are all findings collected throughout the day "
            "(each is the raw output of one crawl):",
            findings_json,
            "",
            "Synthesize these into a single Telegram digest message using this template:",
            "",
            f"📡 {name} - {job.topic}",
            "{Day, Date} · {Time Period}",
            "",
            "▸ {Headline 1} ({Source, Date})",
            "▸ {Headline 2} ({Source, Date})",
            "▸ {Headline 3} ({Source, Date})",
            "",
            "-",
            "{N} sources · {New developments} · Knowledge base updated",
            "Reply with a number (1-{N}) to deep-dive.",
            "",
            "Rules:",
            "- Telegram formatting only: *bold*, _italic_, `mono`. No markdown headers, "
            "tables, or code fences.",
            "- Deduplicate overlapping items, rank by importance, highlight the top 3-5.",
            "- Every item must carry a source. Drop anything you cannot source.",
            "- Append the SAVE_TO_NOTION marker with the full digest data:",
            '[SAVE_TO_NOTION: {"title": "...", "topic": "...", "summary": "2-3 sentences", '
            '"keyFindings": ["..."], "sources": [{"title": "...", "url": "..."}], '
            '"tags": ["..."]}]',
        ]
    )


# A convenience tuple for callers that want to validate / display tone choices.
TONE_CHOICES: tuple[Tone, ...] = ("professional", "casual", "academic", "journalist")
