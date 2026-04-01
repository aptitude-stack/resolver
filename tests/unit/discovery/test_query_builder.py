from __future__ import annotations

from aptitude.discovery.intent import parse_search_intent
from aptitude.discovery.query_builder import build_discovery_query


def test_build_discovery_query_preserves_user_text_and_preferences() -> None:
    intent = parse_search_intent("trusted python lint for ci")

    query = build_discovery_query(intent)

    assert query.name == "trusted python lint for ci"
    assert query.description == "trusted python lint for ci"
    assert query.tags[:3] == ["trusted", "python", "lint"]
    assert query.language == "python"
    assert query.trust_tiers == ["verified"]


def test_build_discovery_query_handles_empty_like_queries_without_crashing() -> None:
    intent = parse_search_intent("   \t   ")

    query = build_discovery_query(intent)

    assert query.tags == []
    assert query.language is None
    assert query.trust_tiers == []
    assert query.description is None


def test_build_discovery_query_preserves_non_latin_user_text() -> None:
    intent = parse_search_intent("מיומנות פוסטמן")

    query = build_discovery_query(intent)

    assert query.name == "מיומנות פוסטמן"
    assert query.tags == []
    assert query.language is None
    assert query.trust_tiers == []


def test_build_discovery_query_caps_tags_for_very_long_input() -> None:
    intent = parse_search_intent("one two three four five six seven eight nine ten")

    query = build_discovery_query(intent)

    assert query.tags == ["one", "two", "three", "four", "five"]
    assert query.description == "one two three four five six seven eight nine ten"
