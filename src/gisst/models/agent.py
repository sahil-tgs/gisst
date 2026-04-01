"""The configurable persona of the agent - its identity, research behaviour,
interaction rules, and default scheduling preferences.

This is the *user layer* that the prompt engine renders on top of the hardcoded
base prompt. Ported from the original ``agent-config.ts``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gisst.constants import DEFAULT_AGENT_NAME, DEFAULT_PROFILE_ID

Tone = Literal["professional", "casual", "academic", "journalist"]
Depth = Literal["quick", "standard", "deep"]
SourcePreference = Literal["news", "academic", "social", "all"]
CiteStyle = Literal["inline", "footnote"]
ResponseLength = Literal["concise", "standard", "detailed"]
TriggerMode = Literal["all", "mention", "command"]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _default_source_preferences() -> list[SourcePreference]:
    return ["all"]


class AgentIdentity(BaseModel):
    name: str = DEFAULT_AGENT_NAME
    tone: Tone = "professional"
    language: str = "en"
    emoji_style: bool = True


class ResearchSettings(BaseModel):
    depth: Depth = "standard"
    topics: list[str] = Field(default_factory=list)
    source_preferences: list[SourcePreference] = Field(default_factory=_default_source_preferences)
    platform_priority: list[str] = Field(default_factory=list)
    auto_cite: CiteStyle = "footnote"


class InteractionSettings(BaseModel):
    response_length: ResponseLength = "standard"
    follow_up: bool = True
    auto_save: bool = True
    trigger_mode: TriggerMode = "command"


class QuietHours(BaseModel):
    start: str = "23:00"
    end: str = "06:00"


class ScheduleSettings(BaseModel):
    max_jobs_per_day: int = 20
    quiet_hours: QuietHours = Field(default_factory=QuietHours)
    default_digest_time: str = "20:00"
    default_timezone: str = "UTC"


class AgentProfile(BaseModel):
    """A complete, persistable agent persona."""

    model_config = ConfigDict(validate_assignment=True)

    id: str = DEFAULT_PROFILE_ID
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    identity: AgentIdentity = Field(default_factory=AgentIdentity)
    research: ResearchSettings = Field(default_factory=ResearchSettings)
    interaction: InteractionSettings = Field(default_factory=InteractionSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)

    @classmethod
    def default(cls) -> AgentProfile:
        """A sensible out-of-the-box persona (the ``Scout`` analyst)."""
        return cls(id=DEFAULT_PROFILE_ID)

    def touch(self) -> None:
        self.updated_at = _utcnow()
