#!/usr/bin/env python
"""One-time Notion provisioning CLI.

Creates the "Research Findings" and "Daily Digests" databases under the parent
page configured via ``NOTION_PAGE_ID`` and prints the resulting database ids so
they can be pasted back into ``.env`` (``NOTION_RESEARCH_DB_ID`` /
``NOTION_DIGEST_DB_ID``). Safe to re-run: provisioning is idempotent.

Usage:
    uv run python scripts/setup_notion.py
"""

from __future__ import annotations

import asyncio
import sys

from gisst.config import get_settings
from gisst.logging import configure_logging, get_logger
from gisst.notion import NotionClient, NotionSchema

log = get_logger("scripts.setup_notion")


async def _provision() -> int:
    settings = get_settings()
    configure_logging(
        level=settings.observability.log_level,
        json_logs=settings.observability.log_json,
    )

    if not settings.notion.enabled:
        log.error(
            "notion is not configured",
            hint="set NOTION_API_KEY and NOTION_PAGE_ID in .env",
        )
        return 1

    client = NotionClient(
        api_key=settings.notion.api_key,
        notion_version=settings.notion.version,
    )
    schema = NotionSchema(client)

    log.info("provisioning notion databases", page_id=settings.notion.page_id)
    try:
        db_ids = await schema.provision(settings.notion.page_id)
    finally:
        # NotionClient may hold an httpx client; close it if it exposes aclose().
        aclose = getattr(client, "aclose", None)
        if callable(aclose):
            await aclose()

    research_db_id = db_ids.get("research_db_id", "")
    digest_db_id = db_ids.get("digest_db_id", "")

    print("Notion databases provisioned. Add these to your .env:\n")
    print(f"NOTION_RESEARCH_DB_ID={research_db_id}")
    print(f"NOTION_DIGEST_DB_ID={digest_db_id}")

    return 0


def main() -> None:
    """Entry point: run the async provisioner and exit with its status code."""
    raise SystemExit(asyncio.run(_provision()))


if __name__ == "__main__":
    sys.exit(asyncio.run(_provision()))
