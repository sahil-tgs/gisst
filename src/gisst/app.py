"""Composition root.

This is the only module that knows about *every* subsystem. It constructs the
object graph, injects collaborators (so no subsystem imports another directly),
and runs the bot, the scheduler, and the optional API dashboard together on one
asyncio event loop.

    Telegram polling -┐
    APScheduler tick -┼- one event loop - shared Repositories / runtime / Notion
    Uvicorn (API)   --┘
"""

from __future__ import annotations

import asyncio
import contextlib

from gisst import __version__
from gisst.agent.profile import ProfileStore
from gisst.agent.queue import AgentQueue, FindingMeta
from gisst.agent.runtime import build_runtime
from gisst.config import Settings, get_settings
from gisst.db import Database, Repositories
from gisst.logging import configure_logging, get_logger
from gisst.models.research import ResearchFinding
from gisst.notion import NotionClient, NotionSchema, NotionSync
from gisst.scheduler import SchedulerService, WatchoutEngine
from gisst.telegram import TelegramBot, TelegramNotifier

log = get_logger("app")


class GisstApplication:
    """Owns the full object graph and lifecycle."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()

        # -- Spine ------------------------------------------------------------
        self.db = Database(self.settings.database.url)
        self.repos = Repositories(self.db)

        # -- Agent core -------------------------------------------------------
        self.runtime = build_runtime(self.settings)
        self.profiles = ProfileStore(self.settings)

        # -- Notion (no-ops gracefully when unconfigured) ---------------------
        self.notion_client = NotionClient(self.settings)
        self.notion_schema = NotionSchema(self.notion_client, self.settings)
        self.notion = NotionSync(self.notion_client, self.notion_schema, self.repos)

        # -- Queue (Notion sync injected as the finding handler) --------------
        self.queue = AgentQueue(
            self.runtime,
            self.repos,
            self.profiles,
            on_finding=self._on_finding,
        )

        # -- Telegram channel -------------------------------------------------
        self.telegram = TelegramBot(self.settings, self.queue, self.repos)
        self.notifier: TelegramNotifier = TelegramNotifier(self.telegram.bot)

        # -- Scheduler + Watchout pipeline ------------------------------------
        self.watchout = WatchoutEngine(
            self.runtime,
            self.repos,
            self.notion,
            self.notifier,
            self.profiles,
        )
        self.scheduler = SchedulerService(self.watchout, self.settings)

        self._tasks: list[asyncio.Task] = []

    async def _on_finding(self, finding: ResearchFinding, meta: FindingMeta) -> None:
        """Mirror a conversational finding into Notion (best effort)."""
        with contextlib.suppress(Exception):
            await self.notion.sync_research(
                finding, researcher=meta.user_name, session_id=meta.session_id
            )

    async def startup(self) -> None:
        log.info(
            "starting gisst",
            version=__version__,
            env=self.settings.env,
            backend=self.runtime.name,
            model=self.settings.agent.model,
        )
        await self.db.create_all()

        if self.settings.notion.enabled:
            try:
                ids = await self.notion_schema.provision(self.settings.notion.page_id)
                log.info("notion connected", **{k: v[:8] for k, v in ids.items()})
            except Exception as exc:
                log.warning("notion provisioning failed; continuing without it", error=str(exc))
        else:
            log.info("notion not configured; knowledge-base sync disabled")

    async def run(self) -> None:
        """Run until interrupted."""
        await self.startup()

        if self.settings.scheduler.enabled:
            self.scheduler.start()

        if self.settings.api.enabled:
            self._tasks.append(asyncio.create_task(self._serve_api(), name="api"))

        try:
            # Telegram polling blocks until the bot is stopped.
            await self.telegram.start()
        finally:
            await self.shutdown()

    async def _serve_api(self) -> None:
        import uvicorn

        from gisst.api import create_api

        api = create_api(self.repos, settings=self.settings, runtime_name=self.runtime.name)
        config = uvicorn.Config(
            api,
            host=self.settings.api.host,
            port=self.settings.api.port,
            log_level=self.settings.observability.log_level.lower(),
            access_log=False,
        )
        server = uvicorn.Server(config)
        log.info(
            "api dashboard listening", host=self.settings.api.host, port=self.settings.api.port
        )
        await server.serve()

    async def shutdown(self) -> None:
        log.info("shutting down")
        with contextlib.suppress(Exception):
            self.scheduler.shutdown()
        with contextlib.suppress(Exception):
            await self.telegram.stop()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        await self.db.dispose()


async def run() -> None:
    settings = get_settings()
    configure_logging(
        level=settings.observability.log_level,
        json_logs=settings.observability.log_json or settings.env == "prod",
    )
    app = GisstApplication(settings)
    await app.run()
