"""Pydantic domain models - the data contracts shared across every subsystem.

These are deliberately framework-agnostic: the Telegram adapter, the Notion
sync layer, the SQLAlchemy ORM, and the agent runtime all speak in terms of
these models rather than raw dicts.
"""

from __future__ import annotations

from gisst.models.agent import (
    AgentIdentity,
    AgentProfile,
    InteractionSettings,
    ResearchSettings,
    ScheduleSettings,
    Tone,
)
from gisst.models.messaging import ChatType, InboundMessage, OutboundMessage
from gisst.models.research import (
    CrawlFinding,
    ResearchFinding,
    ResearchSource,
    StoredDigest,
    StoredFinding,
)
from gisst.models.schedule import ScheduleJob, ScheduleJobState, StagedFinding

__all__ = [
    "AgentIdentity",
    "AgentProfile",
    "ChatType",
    "CrawlFinding",
    "InboundMessage",
    "InteractionSettings",
    "OutboundMessage",
    "ResearchFinding",
    "ResearchSettings",
    "ResearchSource",
    "ScheduleJob",
    "ScheduleJobState",
    "ScheduleSettings",
    "StagedFinding",
    "StoredDigest",
    "StoredFinding",
    "Tone",
]
