"""Aptitude Resolver runtime package."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[import-not-found]


def resolve_package_version() -> str:
    """Return the runtime version from installed metadata or local pyproject."""

    try:
        return package_version("aptitude-resolver")
    except PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with pyproject_path.open("rb") as pyproject_file:
            project = tomllib.load(pyproject_file)["project"]
        return str(project["version"])


__version__ = resolve_package_version()

__all__ = ["__version__", "resolve_package_version"]
