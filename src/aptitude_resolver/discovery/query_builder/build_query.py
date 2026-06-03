"""Build resolver-owned discovery queries from normalized intent."""

from __future__ import annotations

import re

from aptitude_resolver.domain.models import DiscoveryQuery, SearchIntent

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,127})$")


def build_discovery_query(intent: SearchIntent) -> DiscoveryQuery:
    """Convert normalized intent into a discovery query."""

    if _looks_like_slug(intent.raw_query):
        return DiscoveryQuery(
            name=intent.raw_query,
            description=None,
            tags=[],
            language=intent.language,
            trust_tiers=[intent.trust_preference] if intent.trust_preference else [],
        )

    return DiscoveryQuery(
        name=intent.raw_query,
        description=intent.raw_query if len(intent.preferred_labels) > 1 else None,
        tags=list(intent.preferred_tags[:5]),
        language=intent.language,
        trust_tiers=[intent.trust_preference] if intent.trust_preference else [],
    )


def _looks_like_slug(query: str) -> bool:
    return SLUG_RE.fullmatch(query) is not None and " " not in query and "-" in query
