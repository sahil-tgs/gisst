"""The runtime contract shared by every Claude backend.

A runtime takes an :class:`AgentRequest` (a prompt + a system prompt + an
optional session handle) and returns an :class:`AgentResult` (the raw text plus
the resolved session id). Marker parsing and Notion sync happen *above* the
runtime, in the queue/pipeline, so backends stay focused on "talk to Claude".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class RuntimeError_(RuntimeError):
    """Raised when a backend fails to produce a usable response."""


@dataclass(slots=True)
class AgentRequest:
    """Everything a backend needs for one turn."""

    prompt: str
    system_prompt: str
    session_id: str | None = None
    # When True the run is a background/headless job (a Watchout crawl or digest)
    # and no session should be created or persisted.
    headless: bool = False
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResult:
    """The outcome of one runtime turn."""

    text: str
    session_id: str | None = None
    backend: str = ""
    turns: int = 1


@runtime_checkable
class AgentRuntime(Protocol):
    """Protocol every Claude backend implements."""

    name: str

    async def run(self, request: AgentRequest) -> AgentResult:
        """Execute one agent turn and return the raw text result."""
        ...
