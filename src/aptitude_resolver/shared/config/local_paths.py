"""Platform-specific local storage paths for Aptitude-owned state."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def default_aptitude_data_dir(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path:
    """Return the OS-appropriate Aptitude data directory."""

    env_map = os.environ if env is None else env
    effective_home = Path.home() if home is None else home
    effective_os_name = os.name if os_name is None else os_name

    if effective_os_name == "nt":
        local_app_data = env_map.get("LOCALAPPDATA")
        base = (
            Path(local_app_data)
            if local_app_data is not None
            else effective_home / "AppData" / "Local"
        )
        return base / "aptitude"

    xdg_data_home = env_map.get("XDG_DATA_HOME")
    base = (
        Path(xdg_data_home)
        if xdg_data_home is not None
        else effective_home / ".local" / "share"
    )
    return base / "aptitude"


def default_aptitude_cache_dir(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path:
    """Return the OS-appropriate Aptitude cache directory."""

    env_map = os.environ if env is None else env
    effective_home = Path.home() if home is None else home
    effective_os_name = os.name if os_name is None else os_name

    if effective_os_name == "nt":
        return default_aptitude_data_dir(
            env=env_map,
            home=effective_home,
            os_name=effective_os_name,
        ) / "cache"

    xdg_cache_home = env_map.get("XDG_CACHE_HOME")
    base = (
        Path(xdg_cache_home)
        if xdg_cache_home is not None
        else effective_home / ".cache"
    )
    return base / "aptitude" / "cache"


def default_aptitude_state_dir(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path:
    """Return the OS-appropriate Aptitude state directory."""

    env_map = os.environ if env is None else env
    effective_home = Path.home() if home is None else home
    effective_os_name = os.name if os_name is None else os_name

    if effective_os_name == "nt":
        return default_aptitude_data_dir(
            env=env_map,
            home=effective_home,
            os_name=effective_os_name,
        ) / "state"

    xdg_state_home = env_map.get("XDG_STATE_HOME")
    base = (
        Path(xdg_state_home)
        if xdg_state_home is not None
        else effective_home / ".local" / "state"
    )
    return base / "aptitude"


def default_install_materialization_root() -> Path:
    """Return the internal materialization root for fresh installs."""

    return default_aptitude_state_dir() / "install"


def default_sync_materialization_root() -> Path:
    """Return the internal materialization root for lock sync."""

    return default_aptitude_state_dir() / "sync"
