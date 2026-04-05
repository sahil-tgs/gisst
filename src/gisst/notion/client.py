"""Thin async wrapper around the official ``notion-client`` SDK.

The SDK is imported *lazily* (inside the property that builds the client) so
this module (and therefore the rest of the Notion subsystem) imports cleanly
even when ``notion-client`` is not installed. Code paths that never actually
talk to Notion (e.g. when ``settings.notion.enabled`` is false) never trigger
the import.

Faithful port of ``notion/client.ts`` (``getNotion`` / ``createDatabase`` /
``createPage`` / ``queryDatabase``), made async and dependency-injected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gisst.config import Settings
from gisst.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from notion_client import AsyncClient

log = get_logger("notion.client")


class NotionClient:
    """Lazily-constructed async Notion API client.

    The underlying :class:`notion_client.AsyncClient` is built on first use,
    not at construction time, so instantiating ``NotionClient`` is always cheap
    and never requires the ``notion-client`` package to be importable.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncClient | None = None

    @property
    def _api(self) -> AsyncClient:
        """Return the underlying SDK client, building it on first access."""
        if self._client is None:
            api_key = self._settings.notion.api_key
            if not api_key:
                raise RuntimeError("NOTION_API_KEY not set")
            # Imported here so the module loads without notion-client present.
            from notion_client import AsyncClient

            self._client = AsyncClient(
                auth=api_key,
                notion_version=self._settings.notion.version,
            )
            log.debug("notion async client initialised")
        return self._client

    async def create_database(
        self,
        parent_page_id: str,
        title: str,
        properties: dict[str, Any],
    ) -> str:
        """Create a database under ``parent_page_id`` and return its id."""
        db = await self._api.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": title}}],
            properties=properties,
        )
        return str(db["id"])

    async def create_page(
        self,
        database_id: str,
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> str:
        """Create a page inside ``database_id`` and return its id."""
        page = await self._api.pages.create(
            parent={"type": "database_id", "database_id": database_id},
            properties=properties,
            children=children or [],
        )
        return str(page["id"])

    async def query_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,  # mirror Notion API kw name
        sorts: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Query ``database_id`` and return the raw ``results`` list.

        Uses the low-level ``request`` helper rather than ``databases.query``:
        the latter was removed from the SDK's typed endpoint surface in 3.x,
        whereas the raw ``POST /databases/{id}/query`` route is stable across
        every release.
        """
        body: dict[str, Any] = {}
        if filter is not None:
            body["filter"] = filter
        if sorts is not None:
            body["sorts"] = sorts
        response = await self._api.request(
            path=f"databases/{database_id}/query",
            method="POST",
            body=body,
        )
        results = response.get("results", []) if isinstance(response, dict) else []
        return list(results)
