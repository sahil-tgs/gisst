"""The FastAPI application factory for the observability dashboard.

``create_api`` wires a handful of read-only JSON endpoints plus a single HTML
page over the :class:`~gisst.db.repositories.Repositories` aggregate. The page
is rendered from ``templates/dashboard.html`` and refreshes itself client-side
by polling the JSON endpoints, so the server stays stateless and read-only.

Nothing here writes to the database; the dashboard is purely observational and
can be mounted next to the agent without risk.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

import gisst
from gisst.db.repositories import Repositories
from gisst.logging import get_logger

if TYPE_CHECKING:
    from gisst.config import Settings

log = get_logger("api.app")

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _make_jinja_env() -> Environment:
    """Build the Jinja2 environment used to render the dashboard page."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(("html", "xml")),
        enable_async=False,
    )


def create_api(
    repos: Repositories,
    *,
    settings: Settings,
    runtime_name: str,
) -> FastAPI:
    """Construct the read-only observability dashboard.

    Args:
        repos: The repository aggregate. All reads go through it.
        settings: The materialised application settings (used for app metadata).
        runtime_name: Human-readable name of the active agent runtime
            (e.g. ``"claude-cli"``), surfaced on the dashboard.

    Returns:
        A configured :class:`fastapi.FastAPI` instance with ``/`` (HTML),
        ``/health`` and the ``/api/*`` JSON endpoints registered.
    """
    app = FastAPI(
        title="Gisst - Watchout Console",
        description="Read-only observability dashboard for the Gisst research agent.",
        version=gisst.__version__,
        docs_url="/api/docs",
        redoc_url=None,
    )

    jinja_env = _make_jinja_env()

    # -- HTML dashboard --------------------------------------------------------
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard() -> HTMLResponse:
        """Render the single-page console; data is fetched client-side."""
        template = jinja_env.get_template("dashboard.html")
        html = template.render(
            runtime=runtime_name,
            version=gisst.__version__,
            environment=settings.env,
        )
        return HTMLResponse(content=html)

    # -- Liveness / DB probe ---------------------------------------------------
    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Liveness probe plus a one-shot database round-trip check."""
        return {"status": "ok", "db": await repos.db.healthcheck()}

    # -- Aggregate stats -------------------------------------------------------
    @app.get("/api/stats")
    async def stats() -> dict[str, Any]:
        """Counts for the stat cards, plus runtime + version metadata."""
        data = await repos.stats()
        return {
            **data,
            "runtime": runtime_name,
            "version": gisst.__version__,
        }

    # -- Recent findings -------------------------------------------------------
    @app.get("/api/findings")
    async def findings(
        limit: int = Query(50, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        """The most recent stored research/crawl findings, newest first."""
        rows = await repos.research.list_recent_findings(limit=limit)
        return [row.model_dump(mode="json") for row in rows]

    # -- Recent digests --------------------------------------------------------
    @app.get("/api/digests")
    async def digests(
        limit: int = Query(50, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        """The most recent Watchout digests, newest first."""
        rows = await repos.research.list_recent_digests(limit=limit)
        return [row.model_dump(mode="json") for row in rows]

    # -- Schedule jobs ---------------------------------------------------------
    @app.get("/api/jobs")
    async def jobs() -> list[dict[str, Any]]:
        """Every Watchout Protocol job and its current run state."""
        rows = await repos.jobs.list_all()
        return [row.model_dump(mode="json") for row in rows]

    log.info("observability api created", runtime=runtime_name, version=gisst.__version__)
    return app
