from __future__ import annotations

from pathlib import Path

import pytest

from aptitude_resolver.shared.config.aptitude_config import (
    AptitudeConfig,
    ExecutionConfig,
    PolicyConfig,
    SelectionConfig,
    discover_system_config_path,
    discover_user_config_path,
    discover_workspace_config_path,
    load_aptitude_config,
    read_env_execution_overrides,
    read_env_selection_overrides,
    resolve_system_config_path,
    resolve_user_config_path,
)


def test_load_aptitude_config_reads_selection_section(tmp_path) -> None:
    config_path = tmp_path / "aptitude.toml"
    config_path.write_text(
        """
[selection]
profile = "low-cost"
interaction_mode = "always"
""".strip(),
        encoding="utf-8",
    )

    config = load_aptitude_config(config_path)

    assert isinstance(config, AptitudeConfig)
    assert config.selection == SelectionConfig(
        profile="low-cost",
        interaction_mode="always",
    )


def test_load_aptitude_config_reads_policy_section(tmp_path) -> None:
    config_path = tmp_path / "aptitude.toml"
    config_path.write_text(
        """
[policy]
allowed_trust_tiers = ["verified", "internal"]
allowed_lifecycle_statuses = ["published"]
max_token_estimate = 500
max_content_size_bytes = 2048
max_total_token_estimate = 1500
max_total_content_size_bytes = 4096
""".strip(),
        encoding="utf-8",
    )

    config = load_aptitude_config(config_path)

    assert config == AptitudeConfig(
        policy=PolicyConfig(
            allowed_trust_tiers=["verified", "internal"],
            allowed_lifecycle_statuses=["published"],
            max_token_estimate=500,
            max_content_size_bytes=2048,
            max_total_token_estimate=1500,
            max_total_content_size_bytes=4096,
        )
    )


def test_load_aptitude_config_reads_execution_section(tmp_path) -> None:
    config_path = tmp_path / "aptitude.toml"
    config_path.write_text(
        """
[execution]
concurrent_downloads = 8
concurrent_installs = 4
""".strip(),
        encoding="utf-8",
    )

    config = load_aptitude_config(config_path)

    assert config == AptitudeConfig(
        execution=ExecutionConfig(concurrent_downloads=8, concurrent_installs=4)
    )


def test_load_aptitude_config_rejects_invalid_execution_concurrency(tmp_path) -> None:
    config_path = tmp_path / "aptitude.toml"
    config_path.write_text(
        """
[execution]
concurrent_installs = 0
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid aptitude config"):
        load_aptitude_config(config_path)


def test_load_aptitude_config_raises_for_invalid_toml(tmp_path) -> None:
    config_path = tmp_path / "aptitude.toml"
    config_path.write_text("[selection\nprofile = 'low-cost'", encoding="utf-8")

    with pytest.raises(ValueError):
        load_aptitude_config(config_path)


def test_discover_workspace_config_path_returns_local_aptitude_toml(tmp_path) -> None:
    config_path = tmp_path / "aptitude.toml"
    config_path.write_text("", encoding="utf-8")

    discovered = discover_workspace_config_path(tmp_path)

    assert discovered == config_path


def test_discover_user_config_path_uses_windows_appdata(tmp_path) -> None:
    config_dir = tmp_path / "AppData" / "aptitude"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "aptitude.toml"
    config_path.write_text("", encoding="utf-8")

    discovered = discover_user_config_path(
        env={"APPDATA": str(tmp_path / "AppData")},
        os_name="nt",
    )

    assert discovered == config_path


def test_resolve_user_config_path_uses_unix_xdg_home(tmp_path) -> None:
    resolved = resolve_user_config_path(
        env={"XDG_CONFIG_HOME": str(tmp_path / ".xdg")},
        os_name="posix",
    )

    assert resolved == tmp_path / ".xdg" / "aptitude" / "aptitude.toml"


def test_discover_system_config_path_uses_windows_programdata(tmp_path) -> None:
    config_dir = tmp_path / "ProgramData" / "aptitude"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "aptitude.toml"
    config_path.write_text("", encoding="utf-8")

    discovered = discover_system_config_path(
        env={"PROGRAMDATA": str(tmp_path / "ProgramData")},
        os_name="nt",
    )

    assert discovered == config_path


def test_resolve_system_config_path_defaults_to_etc_on_unix() -> None:
    resolved = resolve_system_config_path(os_name="posix")

    assert resolved == Path("/etc/aptitude/aptitude.toml")


def test_read_env_selection_overrides_reads_selection_fields() -> None:
    config = read_env_selection_overrides(
        {
            "APTITUDE_PREFER": "high-trust",
            "APTITUDE_INTERACTION_MODE": "never",
        }
    )

    assert config == SelectionConfig(
        profile="high-trust",
        interaction_mode="never",
    )


def test_read_env_execution_overrides_reads_concurrency_fields() -> None:
    config = read_env_execution_overrides(
        {
            "APTITUDE_CONCURRENT_DOWNLOADS": "8",
            "APTITUDE_CONCURRENT_INSTALLS": "3",
        }
    )

    assert config == ExecutionConfig(concurrent_downloads=8, concurrent_installs=3)


def test_read_env_execution_overrides_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="APTITUDE_CONCURRENT_DOWNLOADS"):
        read_env_execution_overrides({"APTITUDE_CONCURRENT_DOWNLOADS": "0"})
