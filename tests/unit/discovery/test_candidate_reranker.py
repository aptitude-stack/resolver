from __future__ import annotations

from aptitude_client.discovery.intent import parse_search_intent
from aptitude_client.discovery.reranking import rerank_candidates
from aptitude_client.domain.models import (
    DiscoveryCandidate,
    SkillCoordinate,
    VersionSummary,
)
from aptitude_client.domain.policy import SelectionPreferences


def _candidate(
    slug: str,
    version: str,
    *,
    name: str,
    tags: list[str],
    runtime: str,
    trust_tier: str = "internal",
    token_estimate: int = 100,
    content_size_bytes: int = 256,
    published_at: str = "2026-03-18T00:00:00Z",
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        slug=slug,
        selected_version=VersionSummary(
            coordinate=SkillCoordinate(slug=slug, version=version),
            name=name,
            description=f"{name} description",
            tags=tags,
            headers={"runtime": runtime},
            rendered_summary=f"{name} summary",
            lifecycle_status="published",
            trust_tier=trust_tier,
            published_at=published_at,
            content_checksum_algorithm="sha256",
            content_checksum_digest=f"digest-{slug}-{version}",
            content_size_bytes=content_size_bytes,
            token_estimate=token_estimate,
            maturity_score=0.9,
            security_score=0.95,
        ),
        labels=tags + [runtime],
        matched_labels=[],
        match_reasons=["server_candidate"],
    )


def test_rerank_candidates_prefers_exact_name_runtime_and_tags() -> None:
    intent = parse_search_intent("python lint")

    ranked = rerank_candidates(
        intent,
        [
            _candidate(
                "generic.lint",
                "3.0.0",
                name="Generic Lint",
                tags=["lint"],
                runtime="bash",
            ),
            _candidate(
                "python.lint",
                "1.2.3",
                name="Python Lint",
                tags=["python", "lint"],
                runtime="python",
            ),
        ],
        SelectionPreferences(),
    )

    assert [item.slug for item in ranked] == ["python.lint", "generic.lint"]
    assert [item.ranking_position for item in ranked] == [1, 2]


def test_rerank_candidates_prefers_lower_cost_under_low_cost_profile() -> None:
    intent = parse_search_intent("lint tool")
    candidates = [
        _candidate(
            "trusted.lint",
            "1.0.0",
            name="Lint Tool",
            tags=["lint", "tool"],
            runtime="python",
            trust_tier="verified",
            token_estimate=500,
            content_size_bytes=300,
        ),
        _candidate(
            "cheap.lint",
            "1.0.0",
            name="Lint Tool",
            tags=["lint", "tool"],
            runtime="python",
            trust_tier="internal",
            token_estimate=50,
            content_size_bytes=150,
        ),
    ]

    balanced = rerank_candidates(
        intent, candidates, SelectionPreferences(profile="balanced")
    )
    low_cost = rerank_candidates(
        intent, candidates, SelectionPreferences(profile="low-cost")
    )

    assert [item.slug for item in balanced] == ["trusted.lint", "cheap.lint"]
    assert [item.slug for item in low_cost] == ["cheap.lint", "trusted.lint"]


def test_rerank_candidates_low_cost_profile_keeps_relevance_ahead_of_cost() -> None:
    intent = parse_search_intent("python lint")
    candidates = [
        _candidate(
            "python.lint",
            "1.0.0",
            name="Python Lint",
            tags=["python", "lint"],
            runtime="python",
            trust_tier="internal",
            token_estimate=500,
            content_size_bytes=400,
        ),
        _candidate(
            "cheap.tool",
            "1.0.0",
            name="Cheap Tool",
            tags=["tool"],
            runtime="bash",
            trust_tier="internal",
            token_estimate=10,
            content_size_bytes=50,
        ),
    ]

    low_cost = rerank_candidates(
        intent, candidates, SelectionPreferences(profile="low-cost")
    )

    assert [item.slug for item in low_cost] == ["python.lint", "cheap.tool"]
