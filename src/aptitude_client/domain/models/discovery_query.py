"""Domain model for discovery request construction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiscoveryQuery:
    """Client-owned discovery request shape prior to registry transport mapping."""

    name: str
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    language: str | None = None
    trust_tiers: list[str] = field(default_factory=list)
