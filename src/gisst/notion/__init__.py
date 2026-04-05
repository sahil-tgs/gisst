"""Notion knowledge-base integration.

Three collaborators, wired by the composition root:

* :class:`NotionClient`: async wrapper over the ``notion-client`` SDK.
* :class:`NotionSchema`: idempotent database provisioning + id persistence.
* :class:`NotionSync`: turns domain models into Notion pages.
"""

from __future__ import annotations

from gisst.notion.client import NotionClient
from gisst.notion.schema import NotionSchema
from gisst.notion.sync import NotionSync

__all__ = ["NotionClient", "NotionSchema", "NotionSync"]
