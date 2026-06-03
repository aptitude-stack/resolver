from __future__ import annotations

from pathlib import Path

from aptitude_resolver.shared.config import (
    default_aptitude_cache_dir,
    default_aptitude_state_dir,
)


def test_windows_cache_and_state_live_under_local_app_data() -> None:
    env = {"LOCALAPPDATA": "C:/Users/test/AppData/Local"}
    home = Path("C:/Users/test")

    assert default_aptitude_cache_dir(env=env, home=home, os_name="nt") == (
        Path("C:/Users/test/AppData/Local") / "aptitude" / "cache"
    )
    assert default_aptitude_state_dir(env=env, home=home, os_name="nt") == (
        Path("C:/Users/test/AppData/Local") / "aptitude" / "state"
    )


def test_posix_cache_and_state_respect_xdg_locations() -> None:
    env = {
        "XDG_CACHE_HOME": "/tmp/cache-home",
        "XDG_STATE_HOME": "/tmp/state-home",
    }
    home = Path("/home/test")

    assert default_aptitude_cache_dir(env=env, home=home, os_name="posix") == (
        Path("/tmp/cache-home") / "aptitude" / "cache"
    )
    assert default_aptitude_state_dir(env=env, home=home, os_name="posix") == (
        Path("/tmp/state-home") / "aptitude"
    )
