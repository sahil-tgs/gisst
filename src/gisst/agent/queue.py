"""The per-user agent work queue.

This is the orchestration seam between an inbound message and a Claude turn. It
guarantees that messages from the *same* user are processed strictly
sequentially (one Claude session at a time, no interleaving), while messages
from *different* users run in parallel. Sequencing is achieved with a per-user
:class:`asyncio.Lock` created on demand - there is no background worker loop,
each ``enqueue`` call awaits its turn on the user's lock and does the work
in-line, which keeps backpressure honest and the code simple.

Inside the lock the queue:

1. loads the default agent profile,
2. resumes the user's prior Claude session (if any),
3. builds the two-layer system prompt,
4. runs the turn through the injected :class:`AgentRuntime`,
5. persists a freshly-minted session id (first call only),
6. parses the ``[SAVE_TO_NOTION: {...}]`` marker, records any finding to the DB,
   and (when auto-save is on) fires the optional ``on_finding`` callback as a
   detached task so it never blocks the reply,
7. delivers the clean text via the caller-supplied ``on_response``.

Marker parsing lives in :mod:`gisst.agent.markers`; this module only wires it in.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from gisst.agent.markers import parse_notion_marker
from gisst.agent.profile import ProfileStore
from gisst.agent.prompt import build_system_prompt
from gisst.agent.runtime.base import AgentRequest, AgentRuntime
from gisst.constants import NOTION_TYPE_RESEARCH
from gisst.db.repositories import Repositories
from gisst.logging import get_logger
from gisst.models.agent import AgentProfile
from gisst.models.messaging import InboundMessage
from gisst.models.research import ResearchFinding

log = get_logger("agent.queue")

_ERROR_REPLY = "Sorry, I hit an error. Please try again."


@dataclass(slots=True)
class FindingMeta:
    """Side-channel context handed to the ``on_finding`` callback alongside a
    parsed :class:`ResearchFinding` (who produced it, in which session, of what
    kind). Lets the Notion sync layer attribute the row without re-deriving it."""

    user_name: str | None
    session_id: str | None
    type: str


OnFinding = Callable[[ResearchFinding, FindingMeta], Awaitable[None]]
OnResponse = Callable[[str], Awaitable[None]]


class AgentQueue:
    """Serialise agent turns per user; run different users in parallel."""

    def __init__(
        self,
        runtime: AgentRuntime,
        repos: Repositories,
        profiles: ProfileStore,
        on_finding: OnFinding | None = None,
    ) -> None:
        self._runtime = runtime
        self._repos = repos
        self._profiles = profiles
        self._on_finding = on_finding
        self._locks: dict[str, asyncio.Lock] = {}
        # Strong references to detached background tasks so the event loop does
        # not garbage-collect them mid-flight; each task removes itself on done.
        self._background: set[asyncio.Task[None]] = set()

    def _lock_for(self, user_id: str) -> asyncio.Lock:
        """Return (creating on demand) the serialisation lock for ``user_id``."""
        lock = self._locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_id] = lock
        return lock

    async def enqueue(self, message: InboundMessage, on_response: OnResponse) -> None:
        """Process ``message`` and deliver the reply through ``on_response``.

        Holds the per-user lock for the whole turn so the same user is strictly
        sequential. On any failure the user still gets a graceful error reply.
        """
        async with self._lock_for(message.user_id):
            try:
                await self._process(message, on_response)
            except Exception as exc:  # last line of defence - always reply
                log.error(
                    "agent turn failed",
                    user_id=message.user_id,
                    error=str(exc),
                    exc_info=True,
                )
                await on_response(_ERROR_REPLY)

    async def _process(self, message: InboundMessage, on_response: OnResponse) -> None:
        """Run one agent turn end to end (assumes the user lock is held)."""
        log.info(
            "processing message",
            user_id=message.user_id,
            user_name=message.user_name,
            preview=message.text[:80],
        )

        profile = await self._profiles.get_or_create_default()
        prior_session = await self._repos.sessions.get(message.user_id)

        system_prompt = build_system_prompt(
            profile,
            user_name=message.user_name,
            user_id=message.user_id,
            bot_username=message.bot_username,
        )

        result = await self._runtime.run(
            AgentRequest(
                prompt=message.text,
                system_prompt=system_prompt,
                session_id=prior_session,
            )
        )

        # Persist the session id only on the FIRST call for this user.
        if result.session_id and not prior_session:
            await self._repos.sessions.set(message.user_id, result.session_id)

        parsed = parse_notion_marker(result.text)

        if parsed.finding is not None:
            await self._handle_finding(parsed.finding, message, profile, result.session_id)

        await on_response(parsed.clean_text)

    async def _handle_finding(
        self,
        finding: ResearchFinding,
        message: InboundMessage,
        profile: AgentProfile,
        session_id: str | None,
    ) -> None:
        """Always record a finding to the DB; fire ``on_finding`` only if auto-save
        is enabled and a callback is wired in (detached so it never blocks)."""
        await self._repos.research.record_finding(
            finding,
            researcher=message.user_name,
            finding_type=NOTION_TYPE_RESEARCH,
        )

        if self._on_finding is not None and profile.interaction.auto_save:
            meta = FindingMeta(
                user_name=message.user_name,
                session_id=session_id,
                type=NOTION_TYPE_RESEARCH,
            )
            # Detach: Notion sync must not delay the user's reply, and a sync
            # failure must not fail the turn.
            task = asyncio.create_task(self._safe_on_finding(finding, meta))
            self._background.add(task)
            task.add_done_callback(self._background.discard)

    async def _safe_on_finding(self, finding: ResearchFinding, meta: FindingMeta) -> None:
        """Run the ``on_finding`` callback, swallowing and logging any error."""
        assert self._on_finding is not None  # guarded by caller
        try:
            await self._on_finding(finding, meta)
        except Exception as exc:  # background best-effort - never propagate
            log.error("on_finding callback failed", error=str(exc), exc_info=True)

    async def reset_session(self, user_id: str) -> None:
        """Forget the user's Claude session so the next turn starts fresh."""
        await self._repos.sessions.delete(user_id)
        log.info("session reset", user_id=user_id)


__all__ = ["AgentQueue", "FindingMeta"]
