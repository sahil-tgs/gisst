"""Research artefacts: the ``[SAVE_TO_NOTION: {...}]`` payload the agent emits,
plus the structured findings produced by Watchout Protocol crawls.

``ResearchFinding`` accepts the agent's camelCase JSON (``keyFindings``) as well
as snake_case, so the marker parser can validate raw model output directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchSource(BaseModel):
    """A single cited source. Coerces bare URL strings into ``{title, url}``."""

    model_config = ConfigDict(populate_by_name=True)

    title: str = ""
    url: str = ""

    @classmethod
    def coerce(cls, value: Any) -> ResearchSource:
        if isinstance(value, str):
            return cls(url=value, title=value)
        if isinstance(value, dict):
            return cls.model_validate(value)
        if isinstance(value, ResearchSource):
            return value
        return cls()


class ResearchFinding(BaseModel):
    """The structured payload synced to the Notion *Research Findings* database."""

    model_config = ConfigDict(populate_by_name=True)

    title: str
    topic: str = ""
    summary: str = ""
    key_findings: list[str] = Field(default_factory=list, alias="keyFindings")
    sources: list[ResearchSource] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("sources", mode="before")
    @classmethod
    def _coerce_sources(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [ResearchSource.coerce(item) for item in value]
        return value

    @field_validator("key_findings", "tags", mode="before")
    @classmethod
    def _drop_none(cls, value: Any) -> Any:
        return value if value is not None else []


class CrawlFinding(BaseModel):
    """One item from a Watchout crawl's JSON array output."""

    model_config = ConfigDict(populate_by_name=True)

    headline: str = ""
    summary: str = ""
    url: str = ""
    date: str = ""
    relevance: Literal["high", "medium", "low"] = "medium"


# -- Read models (returned by repositories, consumed by the API dashboard) -----


class StoredFinding(BaseModel):
    """A persisted research/crawl row, as surfaced to the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    topic: str = ""
    summary: str = ""
    finding_type: str = "Research"
    researcher: str | None = None
    notion_page_id: str | None = None
    created_at: datetime


class StoredDigest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    summary: str = ""
    finding_count: int = 0
    schedule_id: str | None = None
    notion_page_id: str | None = None
    created_at: datetime
