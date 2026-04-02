"""Async engine + session factory wrapper.

``Database`` owns the engine lifecycle and hands out sessions through an async
context manager. For SQLite it enables WAL mode and foreign keys on every
connection so the prototype behaves like a real database under concurrency.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from gisst.db.base import Base
from gisst.logging import get_logger

log = get_logger("db.engine")


class Database:
    """Thin wrapper around an async engine + sessionmaker."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        self._url = url
        self.engine: AsyncEngine = create_async_engine(url, echo=echo, future=True)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        if url.startswith("sqlite"):
            self._enable_sqlite_pragmas()

    def _enable_sqlite_pragmas(self) -> None:
        @event.listens_for(self.engine.sync_engine, "connect")
        def _set_pragmas(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async def create_all(self) -> None:
        """Create tables from metadata (dev/test convenience; prod uses Alembic)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("database ready", url=self._sanitised_url())

    async def healthcheck(self) -> bool:
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            log.warning("database healthcheck failed", error=str(exc))
            return False

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session, committing on success and rolling back on error."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        await self.engine.dispose()

    def _sanitised_url(self) -> str:
        # Hide credentials if a non-sqlite URL is ever used.
        if "@" in self._url:
            return self._url.split("@", 1)[-1]
        return self._url
