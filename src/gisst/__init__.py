"""Gisst - a self-hosted, Claude-powered autonomous research agent.

An OpenClaw-style personal agent that lives in Telegram, syncs findings to a
Notion knowledge base, and runs scheduled research jobs (the Watchout Protocol).

The package is organised in layers:

    config / logging / models / db    ->  the stable spine (data + infra contracts)
    core                              ->  cross-cutting protocols (Notifier, ...)
    agent                             ->  the Claude runtime, prompts, queue, sessions
    telegram / notion / scheduler     ->  channel + integration adapters
    api                               ->  optional FastAPI observability dashboard
    app                               ->  composition root that wires everything together
"""

from __future__ import annotations

__version__ = "0.6.0"
__all__ = ["__version__"]
