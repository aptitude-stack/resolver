"""Disk-backed advisory cache store used for registry reads."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from diskcache import Cache


def default_cache_dir(
    *,
    env: dict[str, str] | None = None,
    home: Path | None = None,
    os_name: str | None = None,
) -> Path:
    """Return the default OS-appropriate cache directory for Aptitude."""

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
    else:
        xdg_cache_home = env_map.get("XDG_CACHE_HOME")
        base = (
            Path(xdg_cache_home)
            if xdg_cache_home is not None
            else effective_home / ".cache"
        )

    return base / "resolver" / "cache"


class CacheStore:
    """Small wrapper around diskcache that keeps caching clearly advisory."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = (cache_dir or default_cache_dir()).resolve()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(self._cache_dir))

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def get(self, key: str) -> Any | None:
        return self._cache.get(key, default=None)

    def set(self, key: str, value: Any, *, expire: int | None = None) -> None:
        self._cache.set(key, value, expire=expire)

    def close(self) -> None:
        self._cache.close()
