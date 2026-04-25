"""Build resolver-owned discovery queries from normalized intent."""

from __future__ import annotations

from aptitude_resolver.domain.models import DiscoveryQuery, SearchIntent


def build_discovery_query(intent: SearchIntent) -> DiscoveryQuery:
    """Convert normalized intent into a discovery query."""

    return DiscoveryQuery(
        name=intent.raw_query,
        description=intent.raw_query if len(intent.preferred_labels) > 1 else None,
        tags=list(intent.preferred_tags[:5]),
        language=intent.language,
        trust_tiers=[intent.trust_preference] if intent.trust_preference else [],
    )
