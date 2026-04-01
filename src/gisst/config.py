"""Typed configuration loaded from the environment / ``.env``.

Uses ``pydantic-settings`` v2. Each concern is its own settings group so the
env surface stays readable (``settings.telegram.bot_token``,
``settings.notion.api_key`` ...). Groups are instantiated via ``default_factory``
so every group reads its own slice of the environment.

A single cached :func:`get_settings` accessor is the only public entry point -
import that, never the raw ``Settings`` constructor, so every subsystem sees
the same materialised config.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = three parents up from this file (src/gisst/config.py -> repo root).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_BASE_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
    case_sensitive=False,
)


class TelegramSettings(BaseSettings):
    """Telegram Bot API credentials and behaviour."""

    model_config = SettingsConfigDict(**_BASE_CONFIG, env_prefix="TELEGRAM_")

    bot_token: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token)


class AgentSettings(BaseSettings):
    """How the agent talks to Claude.

    Two interchangeable backends: ``cli`` shells out to the Claude Code CLI,
    ``api`` runs a native Anthropic SDK tool-use loop.
    """

    model_config = SettingsConfigDict(**_BASE_CONFIG)

    backend: Literal["cli", "api"] = Field("cli", validation_alias="AGENT_BACKEND")
    model: str = Field("claude-sonnet-4-6", validation_alias="CLAUDE_MODEL")
    anthropic_api_key: str = Field("", validation_alias="ANTHROPIC_API_KEY")
    timeout_seconds: int = Field(300, validation_alias="AGENT_TIMEOUT")
    max_turns: int = Field(12, validation_alias="AGENT_MAX_TURNS")
    work_dir_override: str = Field("", validation_alias="GISST_WORK_DIR")
    data_dir_override: str = Field("", validation_alias="GISST_DATA_DIR")


class NotionSettings(BaseSettings):
    """Notion knowledge-base integration (optional)."""

    model_config = SettingsConfigDict(**_BASE_CONFIG, env_prefix="NOTION_")

    api_key: str = ""
    page_id: str = ""
    research_db_id: str = ""
    digest_db_id: str = ""
    version: str = "2022-06-28"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.page_id)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(**_BASE_CONFIG)

    url: str = Field(
        "sqlite+aiosqlite:///./data/gisst.db",
        validation_alias="DATABASE_URL",
    )

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith("sqlite")


class SchedulerSettings(BaseSettings):
    model_config = SettingsConfigDict(**_BASE_CONFIG, env_prefix="SCHEDULER_")

    tick_seconds: int = 60
    enabled: bool = True


class ApiSettings(BaseSettings):
    """FastAPI observability dashboard (optional)."""

    model_config = SettingsConfigDict(**_BASE_CONFIG, env_prefix="API_")

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(**_BASE_CONFIG)

    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    log_json: bool = Field(False, validation_alias="LOG_JSON")


class Settings(BaseSettings):
    """Root settings aggregate.

    Access the singleton via :func:`get_settings`.
    """

    model_config = SettingsConfigDict(**_BASE_CONFIG)

    env: Literal["dev", "prod", "test"] = Field("dev", validation_alias="GISST_ENV")

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    notion: NotionSettings = Field(default_factory=NotionSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    # -- Derived paths --------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def data_dir(self) -> Path:
        override = self.agent.data_dir_override
        return Path(override) if override else _PROJECT_ROOT / "data"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def work_dir(self) -> Path:
        override = self.agent.work_dir_override
        return Path(override) if override else self.data_dir / "workspace"

    @property
    def config_dir(self) -> Path:
        return self.data_dir / "agents"

    @property
    def session_dir(self) -> Path:
        return self.data_dir / "sessions"

    @property
    def staging_dir(self) -> Path:
        return self.data_dir / "staging"

    def ensure_dirs(self) -> None:
        """Create every runtime directory the app writes to."""
        for directory in (
            self.data_dir,
            self.work_dir,
            self.config_dir,
            self.session_dir,
            self.staging_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
