"""Raw Aptitude config parsing and discovery helpers."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ValidationError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib


class SelectionConfig(BaseModel):
    """Raw selection config values loaded from files or environment."""

    profile: str | None = None
    interaction_mode: str | None = None


class PolicyConfig(BaseModel):
    """Raw policy config values loaded from files."""

    allowed_lifecycle_statuses: list[str] | None = None
    allowed_trust_tiers: list[str] | None = None
    max_token_estimate: int | None = None
    max_content_size_bytes: int | None = None
    max_total_token_estimate: int | None = None
    max_total_content_size_bytes: int | None = None


class AptitudeConfig(BaseModel):
    """Raw workspace or user config loaded from aptitude.toml."""

    selection: SelectionConfig | None = None
    policy: PolicyConfig | None = None


def resolve_user_config_path(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path:
    """Return the canonical user aptitude.toml path for the current platform."""

    env_map = os.environ if env is None else env
    effective_home = Path.home() if home is None else home
    effective_os_name = os.name if os_name is None else os_name

    if effective_os_name == "nt":
        appdata = env_map.get("APPDATA")
        base = (
            Path(appdata)
            if appdata is not None
            else effective_home / "AppData" / "Roaming"
        )
    else:
        xdg_config_home = env_map.get("XDG_CONFIG_HOME")
        base = (
            Path(xdg_config_home)
            if xdg_config_home is not None
            else effective_home / ".config"
        )

    return base / "aptitude" / "aptitude.toml"


def resolve_system_config_path(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path:
    """Return the canonical system aptitude.toml path for the current platform."""

    env_map = os.environ if env is None else env
    effective_home = Path.home() if home is None else home
    effective_os_name = os.name if os_name is None else os_name

    if effective_os_name == "nt":
        program_data = env_map.get("PROGRAMDATA")
        if program_data is not None:
            base = Path(program_data)
        else:
            anchor = effective_home.anchor or "C:\\"
            base = Path(anchor) / "ProgramData"
    else:
        base = Path("/etc")

    return base / "aptitude" / "aptitude.toml"


def load_aptitude_config(path: Path) -> AptitudeConfig:
    """Load one aptitude.toml file into a typed raw config model."""

    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML in {path}: {exc}") from exc

    try:
        return AptitudeConfig.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid aptitude config at {path}: {exc}") from exc


def discover_workspace_config_path(cwd: Path | None = None) -> Path | None:
    """Find the nearest workspace aptitude.toml from the current directory upward."""

    current = (cwd or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / "aptitude.toml"
        if candidate.is_file():
            return candidate
    return None


def discover_user_config_path(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path | None:
    """Return the current user's aptitude.toml path if it exists."""

    candidate = resolve_user_config_path(env=env, home=home, os_name=os_name)
    if candidate.is_file():
        return candidate
    return None


def discover_system_config_path(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path | None:
    """Return the system aptitude.toml path if it exists."""

    candidate = resolve_system_config_path(env=env, home=home, os_name=os_name)
    if candidate.is_file():
        return candidate
    return None


def load_workspace_aptitude_config(cwd: Path | None = None) -> AptitudeConfig | None:
    """Load the nearest workspace aptitude.toml when present."""

    config_path = discover_workspace_config_path(cwd)
    if config_path is None:
        return None
    return load_aptitude_config(config_path)


def load_user_aptitude_config() -> AptitudeConfig | None:
    """Load the current user's aptitude.toml when present."""

    config_path = discover_user_config_path()
    if config_path is None:
        return None
    return load_aptitude_config(config_path)


def load_system_aptitude_config() -> AptitudeConfig | None:
    """Load the system aptitude.toml when present."""

    config_path = discover_system_config_path()
    if config_path is None:
        return None
    return load_aptitude_config(config_path)


def read_env_selection_overrides(
    env: Mapping[str, str] | None = None,
) -> SelectionConfig | None:
    """Read selection preference overrides from environment variables."""

    env_map = os.environ if env is None else env
    profile = env_map.get("APTITUDE_PREFER")
    interaction_mode = env_map.get("APTITUDE_INTERACTION_MODE")
    if profile is None and interaction_mode is None:
        return None
    return SelectionConfig(
        profile=profile,
        interaction_mode=interaction_mode,
    )
