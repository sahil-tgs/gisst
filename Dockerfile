# syntax=docker/dockerfile:1

# -----------------------------------------------------------------------------
# Gisst container image - multi-stage build with uv.
#
# Stage 1 (builder) resolves + installs the project into a self-contained
# virtualenv using uv. Stage 2 (runtime) copies just that venv + the source
# into a slim image, drops to a non-root user, and runs `python -m gisst`.
# -----------------------------------------------------------------------------

ARG PYTHON_VERSION=3.12

# -- Builder ------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

# Pull the uv binary straight from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Install dependencies first (cached) using only the lockfile + manifest, then
# the project itself. The README is referenced by pyproject's `readme` field.
COPY pyproject.toml README.md ./
COPY uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# Now copy the actual source and install the project (editable-free).
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# -- Runtime ------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

# curl is used by the container HEALTHCHECK to probe the API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user the process runs as.
RUN groupadd --system gisst \
    && useradd --system --gid gisst --create-home --home-dir /home/gisst gisst

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

WORKDIR /app

# Bring over the resolved virtualenv and the application code.
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src ./src
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/migrations ./migrations
COPY pyproject.toml README.md ./

# Runtime data (sqlite db, workspace, staging) lives here; owned by the app user.
RUN mkdir -p /app/data && chown -R gisst:gisst /app

USER gisst

EXPOSE 8000

# Probe the FastAPI dashboard's /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${API_PORT}/health" || exit 1

ENTRYPOINT ["python", "-m", "gisst"]
