"""Optional FastAPI observability dashboard.

A small, read-only window onto the running agent: live stat cards, the most
recent research findings, and the state of every Watchout Protocol job. It never
mutates state - it only reads through the :class:`~gisst.db.repositories.Repositories`
aggregate, so it is safe to expose internally without auth.
"""

from __future__ import annotations

from gisst.api.app import create_api

__all__ = ["create_api"]
