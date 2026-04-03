"""Runtime selection.

``build_runtime`` reads ``settings.agent.backend`` and returns the matching
:class:`~gisst.agent.runtime.base.AgentRuntime` implementation. ``cli`` (the
default) shells out to the Claude Code CLI; ``api`` runs a native Anthropic SDK
tool-use loop.
"""

from __future__ import annotations

from gisst.agent.runtime.api import AnthropicApiRuntime
from gisst.agent.runtime.base import AgentRuntime
from gisst.agent.runtime.cli import ClaudeCliRuntime
from gisst.config import Settings


def build_runtime(settings: Settings) -> AgentRuntime:
    """Return the configured Claude backend.

    ``cli`` -> :class:`ClaudeCliRuntime`, anything else -> :class:`AnthropicApiRuntime`.
    """
    if settings.agent.backend == "cli":
        return ClaudeCliRuntime(settings)
    return AnthropicApiRuntime(settings)
