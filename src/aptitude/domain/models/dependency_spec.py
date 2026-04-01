"""Domain model for direct dependency declarations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DependencySpec:
    """One direct dependency declaration authored by the registry."""

    slug: str
    version: str | None = None
    version_constraint: str | None = None
    optional: bool = False
    markers: list[str] = field(default_factory=list)
