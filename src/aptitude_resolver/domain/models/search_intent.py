"""Domain model for normalized discovery intent."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchIntent:
    """Normalized user request used to build discovery queries and ranking rules."""

    raw_query: str
    normalized_query: str
    terms: list[str]
    preferred_tags: list[str] = field(default_factory=list)
    preferred_labels: list[str] = field(default_factory=list)
    language: str | None = None
    trust_preference: str | None = None
