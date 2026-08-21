from __future__ import annotations

from aptitude_resolver.discovery.intent import parse_search_intent
from aptitude_resolver.discovery.query_builder import build_discovery_query
from aptitude_resolver.domain.models import SkillCoordinate


def test_build_discovery_query_keeps_inferred_preferences_out_of_required_tags() -> (
    None
):
    intent = parse_search_intent("trusted python lint for ci")

    query = build_discovery_query(intent)

    assert query.query == "trusted python lint for ci"
    assert query.tags == []
    assert query.context_skills == []


def test_build_discovery_query_does_not_turn_slug_like_query_into_required_tags() -> (
    None
):
    intent = parse_search_intent("python-patterns")

    query = build_discovery_query(intent)

    assert query.query == "python-patterns"
    assert query.tags == []
    assert query.context_skills == []


def test_build_discovery_query_handles_empty_like_queries_without_crashing() -> None:
    intent = parse_search_intent("   \t   ")

    query = build_discovery_query(intent)

    assert query.tags == []
    assert query.context_skills == []


def test_build_discovery_query_preserves_non_latin_user_text() -> None:
    intent = parse_search_intent("מיומנות פוסטמן")

    query = build_discovery_query(intent)

    assert query.query == "מיומנות פוסטמן"
    assert query.tags == []
    assert query.context_skills == []


def test_build_discovery_query_does_not_require_terms_from_long_input_as_tags() -> None:
    intent = parse_search_intent("one two three four five six seven eight nine ten")

    query = build_discovery_query(intent)

    assert query.tags == []
    assert query.query == "one two three four five six seven eight nine ten"


def test_build_discovery_query_does_not_require_natural_language_terms_as_tags() -> (
    None
):
    intent = parse_search_intent("Testing in python")

    query = build_discovery_query(intent)

    assert query.query == "Testing in python"
    assert query.tags == []
    assert query.context_skills == []


def test_build_discovery_query_accepts_lock_context() -> None:
    intent = parse_search_intent("Testing in python")
    context = [SkillCoordinate(slug="python-lint", version="1.2.3")]

    query = build_discovery_query(intent, context_skills=context)

    assert query.context_skills == context
