"""Pluggable Claude runtimes.

Two interchangeable backends implement the :class:`AgentRuntime` protocol:

* :class:`~gisst.agent.runtime.cli.ClaudeCliRuntime` - shells out to the Claude
  Code CLI (``claude -p``), resuming sessions via ``--resume``. Batteries
  included: native WebSearch/WebFetch, file tools, session persistence.
* :class:`~gisst.agent.runtime.api.AnthropicApiRuntime` - a native Anthropic SDK
  tool-use loop, for deployments without the CLI installed.

``build_runtime`` selects one based on configuration.
"""

from __future__ import annotations

from gisst.agent.runtime.base import (
    AgentRequest,
    AgentResult,
    AgentRuntime,
    RuntimeError_,
)
from gisst.agent.runtime.factory import build_runtime

__all__ = [
    "AgentRequest",
    "AgentResult",
    "AgentRuntime",
    "RuntimeError_",
    "build_runtime",
]
