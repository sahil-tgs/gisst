"""Settings smoke tests: the singleton resolves, nested groups exist, and the
derived path properties hang off ``data_dir`` as documented."""

from __future__ import annotations

from pathlib import Path

from gisst.config import (
    AgentSettings,
    ApiSettings,
    DatabaseSettings,
    NotionSettings,
    ObservabilitySettings,
    SchedulerSettings,
    Settings,
    TelegramSettings,
    get_settings,
)


def test_get_settings_returns_settings() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_get_settings_is_cached() -> None:
    # lru_cache means the same object is returned every call.
    assert get_settings() is get_settings()


def test_nested_groups_exist_and_are_typed() -> None:
    s = get_settings()
    assert isinstance(s.telegram, TelegramSettings)
    assert isinstance(s.agent, AgentSettings)
    assert isinstance(s.notion, NotionSettings)
    assert isinstance(s.database, DatabaseSettings)
    assert isinstance(s.scheduler, SchedulerSettings)
    assert isinstance(s.api, ApiSettings)
    assert isinstance(s.observability, ObservabilitySettings)


def test_derived_paths_hang_off_data_dir() -> None:
    s = Settings()
    assert isinstance(s.data_dir, Path)
    assert s.config_dir == s.data_dir / "agents"
    assert s.session_dir == s.data_dir / "sessions"
    assert s.staging_dir == s.data_dir / "staging"
    # work_dir defaults under data_dir when no override is set.
    assert s.work_dir == s.data_dir / "workspace"


def test_data_dir_override_redirects_derived_paths() -> None:
    # ``data_dir_override`` binds to the ``GISST_DATA_DIR`` validation alias.
    s = Settings(agent=AgentSettings(GISST_DATA_DIR="/tmp/gisst-test-xyz"))
    assert s.data_dir == Path("/tmp/gisst-test-xyz")
    assert s.config_dir == Path("/tmp/gisst-test-xyz/agents")
    assert s.work_dir == Path("/tmp/gisst-test-xyz/workspace")


def test_ensure_dirs_creates_runtime_tree(tmp_path) -> None:
    s = Settings(agent=AgentSettings(GISST_DATA_DIR=str(tmp_path / "rt")))
    s.ensure_dirs()
    for directory in (s.data_dir, s.work_dir, s.config_dir, s.session_dir, s.staging_dir):
        assert directory.is_dir()
