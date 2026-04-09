"""Domain-model contracts: the ``keyFindings`` alias, bare-string source coercion,
``ScheduleJob.short_id``, and ``AgentProfile.default``."""

from __future__ import annotations

from gisst.constants import DEFAULT_AGENT_NAME, DEFAULT_PROFILE_ID
from gisst.models import (
    AgentProfile,
    ResearchFinding,
    ResearchSource,
    ScheduleJob,
)


def test_research_finding_accepts_keyfindings_alias() -> None:
    finding = ResearchFinding.model_validate({"title": "T", "keyFindings": ["a", "b"]})
    assert finding.key_findings == ["a", "b"]


def test_research_finding_accepts_snake_case_too() -> None:
    # populate_by_name=True means the canonical snake_case name also works.
    finding = ResearchFinding(title="T", key_findings=["x"])
    assert finding.key_findings == ["x"]


def test_research_finding_coerces_bare_string_sources() -> None:
    finding = ResearchFinding.model_validate(
        {
            "title": "T",
            "sources": [
                "https://example.com/article",
                {"title": "Named", "url": "https://named.com"},
            ],
        }
    )
    assert len(finding.sources) == 2
    first = finding.sources[0]
    assert isinstance(first, ResearchSource)
    assert first.url == "https://example.com/article"
    assert first.title == "https://example.com/article"
    second = finding.sources[1]
    assert second.title == "Named"
    assert second.url == "https://named.com"


def test_research_finding_drops_none_list_fields() -> None:
    finding = ResearchFinding.model_validate({"title": "T", "keyFindings": None, "tags": None})
    assert finding.key_findings == []
    assert finding.tags == []


def test_schedule_job_short_id_is_first_eight_chars() -> None:
    job = ScheduleJob(topic="Quantum computing")
    assert job.short_id == job.id[:8]
    assert len(job.short_id) == 8


def test_agent_profile_default() -> None:
    profile = AgentProfile.default()
    assert profile.id == DEFAULT_PROFILE_ID
    assert profile.identity.name == DEFAULT_AGENT_NAME
    # Default persona ships with auto-save on (so research syncs to Notion).
    assert profile.interaction.auto_save is True
