"""Persistence for :class:`~gisst.models.agent.AgentProfile`.

The prototype keeps each profile as a small JSON file under
``settings.config_dir/<id>.json``. Profiles are tiny and read rarely, so plain
file I/O (offloaded to a thread so we never block the event loop) is more than
enough; a SQLite-backed store can drop in later behind the same interface.

The store is intentionally narrow: load, save, get-or-create-default, and a
field-level ``update`` that merges nested settings.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from gisst.config import Settings
from gisst.constants import DEFAULT_PROFILE_ID
from gisst.logging import get_logger
from gisst.models.agent import AgentProfile

log = get_logger("agent.profile")


class ProfileStore:
    """Load and persist agent profiles as JSON files."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # -- Paths -----------------------------------------------------------------

    def _path(self, profile_id: str) -> Path:
        return self._settings.config_dir / f"{profile_id}.json"

    # -- Reads -----------------------------------------------------------------

    async def load(self, profile_id: str) -> AgentProfile | None:
        """Return the persisted profile, or ``None`` if it does not exist."""
        path = self._path(profile_id)
        raw = await asyncio.to_thread(self._read_raw, path)
        if raw is None:
            return None
        try:
            return AgentProfile.model_validate(raw)
        except ValueError as exc:
            log.warning("invalid profile on disk", profile_id=profile_id, error=str(exc))
            return None

    async def get_or_create_default(self) -> AgentProfile:
        """Return the default profile, creating and persisting it on first run."""
        existing = await self.load(DEFAULT_PROFILE_ID)
        if existing is not None:
            return existing

        profile = AgentProfile.default()
        await self.save(profile)
        log.info("created default agent profile", profile_id=profile.id)
        return profile

    # -- Writes ----------------------------------------------------------------

    async def save(self, profile: AgentProfile) -> None:
        """Persist ``profile`` to disk, stamping ``updated_at``."""
        profile.touch()
        path = self._path(profile.id)
        data = profile.model_dump(mode="json")
        await asyncio.to_thread(self._write_raw, path, data)
        log.debug("profile saved", profile_id=profile.id)

    async def update(self, profile_id: str, **changes: Any) -> AgentProfile | None:
        """Merge ``changes`` into the stored profile and persist it.

        Nested settings groups (``identity``, ``research``, ``interaction``,
        ``schedule``) are merged field-by-field when the change value is a dict,
        so callers can patch a single nested field without resupplying the whole
        group. Returns the updated profile, or ``None`` if it does not exist.
        """
        profile = await self.load(profile_id)
        if profile is None:
            return None

        current = profile.model_dump(mode="json")
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(current.get(key), dict):
                current[key] = {**current[key], **value}
            else:
                current[key] = value

        try:
            updated = AgentProfile.model_validate(current)
        except ValueError as exc:
            log.warning("rejected invalid profile update", profile_id=profile_id, error=str(exc))
            return None

        await self.save(updated)
        return updated

    # -- Blocking helpers (run in a worker thread) -----------------------------

    @staticmethod
    def _read_raw(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("failed to read profile file", path=str(path), error=str(exc))
            return None

    @staticmethod
    def _write_raw(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
