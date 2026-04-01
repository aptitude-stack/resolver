"""Aptitude package."""

from __future__ import annotations

from importlib import metadata

try:
    __version__ = metadata.version("aptitude")
except metadata.PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
