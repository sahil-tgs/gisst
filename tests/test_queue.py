"""End-to-end-ish test of :class:`AgentQueue` with a fake runtime, a real
:class:`Repositories` over a temp DB, and a real :class:`ProfileStore` over a
temp config dir (the ``settings`` fixture). Asserts marker stripping, finding
persistence, and strict per-user serialisation."""

from __future__ import annotations

import asyncio

from gisst.agent.profile import ProfileStore
from gisst.agent.queue import AgentQueue
from gisst.agent.runtime.base import AgentRequest, AgentResult
from gisst.config import Settings
from gisst.db.repositories import Repositories
from gisst.models.messaging import ChatType, InboundMessage

_MARKER_TEXT = (
    "Here is your brief.\n\n"
    '[SAVE_TO_NOTION: {"title": "Fusion", "topic": "Energy", '
    '"summary": "A breakthrough.", "keyFindings": ["net gain"], '
    '"sources": [{"title": "Lab", "url": "https://lab.gov"}], "tags": ["energy"]}]'
)


class FakeRuntime:
    """An :class:`AgentRuntime` that returns a canned result.

    ``response_text`` is the text every run returns. A fresh ``session_id`` is
    handed back on the first call so the queue persists it. ``run`` records the
    prompts it saw (for ordering assertions) and can optionally pause on a
    per-prompt event so two concurrent turns can be deliberately interleaved.
    """

    name = "fake"

    def __init__(
        self,
        response_text: str,
        *,
        gate: asyncio.Event | None = None,
        gate_on: str | None = None,
    ) -> None:
        self._response_text = response_text
        self._gate = gate
        self._gate_on = gate_on
        self.calls: list[str] = []
        self.started: list[str] = []

    async def run(self, request: AgentRequest) -> AgentResult:
        self.started.append(request.prompt)
        # If this is the gated prompt, block until released - lets the test prove
        # a second same-user turn cannot start while this one is in flight.
        if self._gate is not None and request.prompt == self._gate_on:
            await self._gate.wait()
        self.calls.append(request.prompt)
        return AgentResult(
            text=self._response_text,
            session_id="sess-fixed",
            backend=self.name,
        )


def _message(text: str, *, user_id: str = "u1", user_name: str = "Alice") -> InboundMessage:
    return InboundMessage(
        chat_id="chat-1",
        chat_type=ChatType.PRIVATE,
        user_id=user_id,
        user_name=user_name,
        text=text,
    )


async def test_enqueue_strips_marker_and_records_finding(
    settings: Settings, repos: Repositories
) -> None:
    runtime = FakeRuntime(_MARKER_TEXT)
    profiles = ProfileStore(settings)
    queue = AgentQueue(runtime, repos, profiles)

    replies: list[str] = []

    async def on_response(text: str) -> None:
        replies.append(text)

    await queue.enqueue(_message("Tell me about fusion"), on_response)

    # The user-facing reply has the marker stripped.
    assert replies == ["Here is your brief."]
    assert all("SAVE_TO_NOTION" not in r for r in replies)

    # A finding row was recorded, attributed to the sender.
    assert await repos.research.count_findings() == 1
    stored = await repos.research.list_recent_findings()
    assert stored[0].title == "Fusion"
    assert stored[0].researcher == "Alice"


async def test_session_persisted_on_first_call_only(
    settings: Settings, repos: Repositories
) -> None:
    runtime = FakeRuntime("plain reply, no marker")
    queue = AgentQueue(runtime, repos, ProfileStore(settings))

    async def on_response(_: str) -> None:
        pass

    assert await repos.sessions.get("u1") is None
    await queue.enqueue(_message("hello"), on_response)
    assert await repos.sessions.get("u1") == "sess-fixed"


async def test_no_finding_when_response_has_no_marker(
    settings: Settings, repos: Repositories
) -> None:
    runtime = FakeRuntime("just a chat reply")
    queue = AgentQueue(runtime, repos, ProfileStore(settings))

    replies: list[str] = []

    async def on_response(text: str) -> None:
        replies.append(text)

    await queue.enqueue(_message("hi"), on_response)
    assert replies == ["just a chat reply"]
    assert await repos.research.count_findings() == 0


async def test_per_user_serialisation(settings: Settings, repos: Repositories) -> None:
    """Two enqueues for the same user must run strictly in order: the second turn
    cannot begin until the first releases the user lock."""
    gate = asyncio.Event()
    runtime = FakeRuntime("plain reply", gate=gate, gate_on="first")
    queue = AgentQueue(runtime, repos, ProfileStore(settings))

    order: list[str] = []

    async def on_response_first(_: str) -> None:
        order.append("first-done")

    async def on_response_second(_: str) -> None:
        order.append("second-done")

    first = asyncio.create_task(queue.enqueue(_message("first"), on_response_first))
    # Let the first task reach the runtime and block on the gate.
    await asyncio.sleep(0.05)
    second = asyncio.create_task(queue.enqueue(_message("second"), on_response_second))
    await asyncio.sleep(0.05)

    # The first turn is gated (started but not completed); the second must not
    # even have started its runtime call yet because the user lock is held.
    assert runtime.started == ["first"]
    assert "second" not in runtime.started

    # Release the first turn; both should now complete in order.
    gate.set()
    await asyncio.gather(first, second)

    assert runtime.calls == ["first", "second"]
    assert order == ["first-done", "second-done"]


async def test_different_users_run_in_parallel(settings: Settings, repos: Repositories) -> None:
    """A blocked turn for user A must not stall a turn for user B (independent
    per-user locks)."""
    gate = asyncio.Event()
    runtime = FakeRuntime("plain reply", gate=gate, gate_on="from-a")
    queue = AgentQueue(runtime, repos, ProfileStore(settings))

    done: list[str] = []

    async def on_response_b(_: str) -> None:
        done.append("b-done")

    task_a = asyncio.create_task(
        queue.enqueue(_message("from-a", user_id="a"), lambda _t: asyncio.sleep(0))
    )
    await asyncio.sleep(0.05)  # let A reach the gate
    task_b = asyncio.create_task(queue.enqueue(_message("from-b", user_id="b"), on_response_b))

    # B should finish while A is still gated.
    await asyncio.wait_for(task_b, timeout=1.0)
    assert done == ["b-done"]
    assert not task_a.done()

    gate.set()
    await asyncio.wait_for(task_a, timeout=1.0)
