"""Async persistence layer (SQLAlchemy 2.0 + aiosqlite).

The original prototype stored everything in JSON files; this is the
"over-built" replacement: a real async ORM with a repository layer, Alembic
migrations, and read-models that never leak SQLAlchemy objects past the
repository boundary.
"""

from __future__ import annotations

from gisst.db.base import Base
from gisst.db.engine import Database
from gisst.db.repositories import (
    GroupRepository,
    Repositories,
    ResearchRepository,
    ScheduleJobRepository,
    SessionRepository,
    StagingRepository,
)

__all__ = [
    "Base",
    "Database",
    "GroupRepository",
    "Repositories",
    "ResearchRepository",
    "ScheduleJobRepository",
    "SessionRepository",
    "StagingRepository",
]
