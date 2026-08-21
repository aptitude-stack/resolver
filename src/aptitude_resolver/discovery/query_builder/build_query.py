"""Build resolver-owned discovery queries from normalized intent."""

from __future__ import annotations

from aptitude_resolver.domain.models import (
    DiscoveryQuery,
    SearchIntent,
    SkillCoordinate,
)


def build_discovery_query(
    intent: SearchIntent,
    *,
    context_skills: list[SkillCoordinate] | None = None,
) -> DiscoveryQuery:
    """Convert normalized intent into a discovery query."""

    return DiscoveryQuery(
        query=intent.raw_query,
        tags=[],
        context_skills=list(context_skills or []),
    )
