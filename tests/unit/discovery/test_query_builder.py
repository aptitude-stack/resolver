from __future__ import annotations

from aptitude_client.discovery.intent import parse_search_intent
from aptitude_client.discovery.query_builder import build_discovery_query



def test_build_discovery_query_preserves_user_text_and_preferences() -> None:
    intent = parse_search_intent("trusted python lint for ci")

    query = build_discovery_query(intent)

    assert query.name == "trusted python lint for ci"
    assert query.description == "trusted python lint for ci"
    assert query.tags[:3] == ["trusted", "python", "lint"]
    assert query.language == "python"
    assert query.trust_tiers == ["verified"]
