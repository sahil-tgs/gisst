"""Notion database provisioning.

Creates the two knowledge-base databases (*Research Findings* and *Daily
Digests*) under a parent page, exactly once. The resulting database ids are
persisted to ``<config_dir>/notion-databases.json`` and reused on subsequent
boots, so ``provision`` is idempotent.

Port of ``notion/schema.ts`` (``setupNotionDatabases`` / ``getNotionDatabaseIds``).
The persisted dict keeps the original camelCase keys (``research_db`` /
``digest_db``) for parity with the rest of the codebase contract.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from gisst.config import Settings
from gisst.constants import (
    NOTION_TYPE_CRAWL,
    NOTION_TYPE_DIGEST,
    NOTION_TYPE_RESEARCH,
)
from gisst.logging import get_logger
from gisst.notion.client import NotionClient

log = get_logger("notion.schema")

_IDS_FILENAME = "notion-databases.json"


class NotionSchema:
    """Provisions and locates the Notion databases for an agent profile."""

    def __init__(self, client: NotionClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @property
    def _ids_path(self) -> Path:
        return self._settings.config_dir / _IDS_FILENAME

    async def get_database_ids(self) -> dict[str, str] | None:
        """Return the persisted ``{"research_db", "digest_db"}`` ids or ``None``.

        Reads the on-disk cache off the event loop. Returns ``None`` when the
        databases have not been provisioned yet (or the file is unreadable).
        """
        return await asyncio.to_thread(self._read_ids)

    def _read_ids(self) -> dict[str, str] | None:
        path = self._ids_path
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("could not read notion database ids", error=str(exc))
            return None
        if not isinstance(data, dict):
            return None
        research = data.get("research_db")
        digest = data.get("digest_db")
        if not research or not digest:
            return None
        return {"research_db": str(research), "digest_db": str(digest)}

    def _write_ids(self, ids: dict[str, str]) -> None:
        path = self._ids_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")

    async def provision(self, parent_page_id: str) -> dict[str, str]:
        """Ensure both databases exist; create them if needed.

        Idempotent: if ids are already persisted they are returned untouched,
        and Notion is never called.
        """
        existing = await self.get_database_ids()
        if existing:
            log.info("notion databases already provisioned")
            return existing

        log.info("creating Research Findings database")
        research_db = await self._client.create_database(
            parent_page_id,
            "Research Findings",
            self._research_properties(),
        )

        log.info("creating Daily Digests database")
        digest_db = await self._client.create_database(
            parent_page_id,
            "Daily Digests",
            self._digest_properties(),
        )

        ids = {"research_db": research_db, "digest_db": digest_db}
        await asyncio.to_thread(self._write_ids, ids)
        log.info(
            "notion databases created",
            research=research_db[:8],
            digest=digest_db[:8],
        )
        return ids

    # -- Property schemas ------------------------------------------------------

    @staticmethod
    def _research_properties() -> dict[str, Any]:
        """Property schema for the *Research Findings* database."""
        return {
            "Title": {"title": {}},
            "Topic": {"select": {"options": []}},
            "Summary": {"rich_text": {}},
            "Sources": {"rich_text": {}},
            "Tags": {"multi_select": {"options": []}},
            "Date": {"date": {}},
            "Researcher": {"rich_text": {}},
            "Session ID": {"rich_text": {}},
            "Type": {
                "select": {
                    "options": [
                        {"name": NOTION_TYPE_RESEARCH, "color": "blue"},
                        {"name": NOTION_TYPE_CRAWL, "color": "green"},
                        {"name": NOTION_TYPE_DIGEST, "color": "purple"},
                    ],
                },
            },
        }

    @staticmethod
    def _digest_properties() -> dict[str, Any]:
        """Property schema for the *Daily Digests* database."""
        return {
            "Title": {"title": {}},
            "Topic": {"rich_text": {}},
            "Date": {"date": {}},
            "Finding Count": {"number": {}},
            "Schedule ID": {"rich_text": {}},
            "Summary": {"rich_text": {}},
        }
