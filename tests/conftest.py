"""Shared pytest fixtures.

``asyncio_mode = "auto"`` is set in ``pyproject.toml``, so async test functions
and async fixtures need no explicit ``@pytest.mark.asyncio`` / decorator.

The :func:`db` fixture spins up a fresh on-disk SQLite database per test (a real
file under pytest's ``tmp_path`` so WAL pragmas and async I/O behave like prod),
creates the schema, and disposes the engine on teardown. :func:`repos` layers a
:class:`Repositories` over it. :func:`settings` builds a self-contained
:class:`Settings` whose ``data_dir`` lives under ``tmp_path``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from gisst.config import (
    AgentSettings,
    DatabaseSettings,
    Settings,
)
from gisst.db.engine import Database
from gisst.db.repositories import Repositories


@pytest.fixture
def db_url(tmp_path) -> str:
    """An aiosqlite URL pointing at a temp-file database."""
    return "sqlite+aiosqlite:///" + str(tmp_path / "t.db")


@pytest.fixture
async def db(db_url: str) -> AsyncIterator[Database]:
    """A function-scoped :class:`Database` with its schema created.

    The engine is disposed on teardown so no connections leak between tests.
    """
    database = Database(db_url)
    await database.create_all()
    try:
        yield database
    finally:
        await database.dispose()


@pytest.fixture
def repos(db: Database) -> Repositories:
    """A :class:`Repositories` aggregate over the temp database."""
    return Repositories(db)


@pytest.fixture
def settings(tmp_path, db_url: str) -> Settings:
    """A self-contained :class:`Settings` whose runtime dirs live under tmp_path.

    Pointing ``data_dir`` at a temp directory keeps profile/session files out of
    the real ``data/`` tree, and ``ensure_dirs`` is called so callers that write
    to ``config_dir`` etc. find them present.
    """
    data_dir = tmp_path / "data"
    # ``data_dir_override`` is populated via its ``GISST_DATA_DIR`` validation
    # alias (pydantic-settings binds the field to the alias name, not the Python
    # attribute name), so we pass it under that key.
    s = Settings(
        agent=AgentSettings(GISST_DATA_DIR=str(data_dir)),
        database=DatabaseSettings(DATABASE_URL=db_url),
    )
    s.ensure_dirs()
    return s
