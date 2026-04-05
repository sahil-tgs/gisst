"""Sync layer: turn domain models into Notion pages.

Three entry points mirror the original ``notion/sync.ts``:

* :meth:`NotionSync.sync_research`: a :class:`ResearchFinding` (from a
  ``[SAVE_TO_NOTION]`` marker) into the *Research Findings* database.
* :meth:`NotionSync.sync_crawl`: a single Watchout crawl result.
* :meth:`NotionSync.sync_digest`: a daily digest into the *Daily Digests*
  database.

Every method is a safe no-op (returns ``None`` after logging) when the
databases have not been provisioned, when Notion is disabled, or when the
Notion API raises. Returning ``None`` lets callers persist locally regardless.

When a ``Repositories`` instance is injected, successful syncs also record the
row locally with the returned Notion page id so the dashboard can link out.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from gisst.constants import (
    NOTION_TEXT_LIMIT,
    NOTION_TYPE_CRAWL,
    NOTION_TYPE_RESEARCH,
)
from gisst.db.repositories import Repositories
from gisst.logging import get_logger
from gisst.models.research import ResearchFinding
from gisst.notion.client import NotionClient
from gisst.notion.schema import NotionSchema

log = get_logger("notion.sync")


def _today() -> str:
    """ISO date (``YYYY-MM-DD``) in UTC, matching the TS ``toISOString`` split."""
    return datetime.now(UTC).date().isoformat()


def _truncate(text: str) -> str:
    return text[:NOTION_TEXT_LIMIT]


def _rich_text(content: str) -> dict[str, Any]:
    """Wrap a string in a Notion ``rich_text`` property value (truncated)."""
    return {"rich_text": [{"text": {"content": _truncate(content)}}]}


def _title(content: str) -> dict[str, Any]:
    return {"title": [{"text": {"content": _truncate(content)}}]}


def _bullet(content: str) -> dict[str, Any]:
    """A ``bulleted_list_item`` block for a single key finding."""
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": _truncate(content)}}],
        },
    }


def _paragraph(content: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": _truncate(content)}}],
        },
    }


def _format_sources(finding: ResearchFinding) -> str:
    """Render sources as ``[1] Title: url`` lines (the TS format)."""
    return "\n".join(f"[{i + 1}] {src.title}: {src.url}" for i, src in enumerate(finding.sources))


class NotionSync:
    """Writes findings, crawls, and digests to the provisioned Notion databases."""

    def __init__(
        self,
        client: NotionClient,
        schema: NotionSchema,
        repos: Repositories | None = None,
    ) -> None:
        self._client = client
        self._schema = schema
        self._repos = repos

    @property
    def enabled(self) -> bool:
        """Whether Notion integration is configured (api key + parent page)."""
        return self._schema._settings.notion.enabled

    async def _database_ids(self) -> dict[str, str] | None:
        """Return provisioned ids, logging a skip when absent."""
        ids = await self._schema.get_database_ids()
        if ids is None:
            log.info("notion not provisioned, skipping sync")
        return ids

    async def sync_research(
        self,
        finding: ResearchFinding,
        *,
        researcher: str | None = None,
        session_id: str | None = None,
    ) -> str | None:
        """Sync a research finding; return the created Notion page id or ``None``."""
        ids = await self._database_ids()
        if ids is None:
            return None

        properties: dict[str, Any] = {
            "Title": _title(finding.title),
            "Summary": _rich_text(finding.summary or ""),
            "Sources": _rich_text(_format_sources(finding)),
            "Date": {"date": {"start": _today()}},
            "Type": {"select": {"name": NOTION_TYPE_RESEARCH}},
        }
        if finding.topic:
            properties["Topic"] = {"select": {"name": finding.topic}}
        if finding.tags:
            properties["Tags"] = {"multi_select": [{"name": tag} for tag in finding.tags[:10]]}
        if researcher:
            properties["Researcher"] = _rich_text(researcher)
        if session_id:
            properties["Session ID"] = _rich_text(session_id)

        children = [_bullet(item) for item in finding.key_findings]

        try:
            page_id = await self._client.create_page(ids["research_db"], properties, children)
        except Exception as exc:  # never let a Notion failure break the caller
            log.warning("failed to sync research", title=finding.title, error=str(exc))
            return None

        log.info("synced research", title=finding.title, page_id=page_id[:8])
        await self._record_finding(
            finding,
            researcher=researcher,
            finding_type=NOTION_TYPE_RESEARCH,
            page_id=page_id,
        )
        return page_id

    async def sync_crawl(
        self,
        topic: str,
        content: str,
        schedule_id: str,
    ) -> str | None:
        """Sync one Watchout crawl result into the Research database."""
        ids = await self._database_ids()
        if ids is None:
            return None

        properties: dict[str, Any] = {
            "Title": _title(f"{topic} - Crawl {_today()}"),
            "Topic": {"select": {"name": topic}},
            "Summary": _rich_text(content),
            "Date": {"date": {"start": _today()}},
            "Session ID": _rich_text(schedule_id),
            "Type": {"select": {"name": NOTION_TYPE_CRAWL}},
        }

        try:
            page_id = await self._client.create_page(ids["research_db"], properties)
        except Exception as exc:  # never let a Notion failure break the caller
            log.warning("failed to sync crawl", topic=topic, error=str(exc))
            return None

        log.info("synced crawl", topic=topic, page_id=page_id[:8])
        if self._repos is not None:
            finding = ResearchFinding(
                title=f"{topic} - Crawl {_today()}",
                topic=topic,
                summary=content,
            )
            await self._record_finding(
                finding,
                researcher=None,
                finding_type=NOTION_TYPE_CRAWL,
                page_id=page_id,
            )
        return page_id

    async def sync_digest(
        self,
        topic: str,
        summary: str,
        finding_count: int,
        schedule_id: str,
    ) -> str | None:
        """Sync a daily digest into the Digest database."""
        ids = await self._database_ids()
        if ids is None:
            return None

        properties: dict[str, Any] = {
            "Title": _title(f"{topic} - {_today()}"),
            "Topic": _rich_text(topic),
            "Date": {"date": {"start": _today()}},
            "Finding Count": {"number": finding_count},
            "Schedule ID": _rich_text(schedule_id),
            "Summary": _rich_text(summary),
        }
        children = [_paragraph(summary)]

        try:
            page_id = await self._client.create_page(ids["digest_db"], properties, children)
        except Exception as exc:  # never let a Notion failure break the caller
            log.warning("failed to sync digest", topic=topic, error=str(exc))
            return None

        log.info("synced digest", topic=topic, page_id=page_id[:8])
        if self._repos is not None:
            await self._repos.research.record_digest(
                topic=topic,
                summary=summary,
                finding_count=finding_count,
                schedule_id=schedule_id,
                notion_page_id=page_id,
            )
        return page_id

    async def _record_finding(
        self,
        finding: ResearchFinding,
        *,
        researcher: str | None,
        finding_type: str,
        page_id: str,
    ) -> None:
        """Persist the finding locally with its Notion page id (best effort)."""
        if self._repos is None:
            return
        try:
            await self._repos.research.record_finding(
                finding,
                researcher=researcher,
                finding_type=finding_type,
                notion_page_id=page_id,
            )
        except Exception as exc:  # local persistence is best-effort
            log.warning("failed to record finding locally", error=str(exc))


__all__ = ["NotionSync"]
