"""Deterministic client-side discovery reranking."""

from __future__ import annotations

from dataclasses import replace

from packaging.version import Version

from aptitude_client.discovery.intent import normalize_text
from aptitude_client.domain.models import DiscoveryCandidate, SearchIntent
from aptitude_client.domain.policy import (
    SelectionPreferences,
    lifecycle_status_rank,
    trust_tier_rank,
)


def rerank_candidates(
    intent: SearchIntent,
    candidates: list[DiscoveryCandidate],
    selection_preferences: SelectionPreferences,
) -> list[DiscoveryCandidate]:
    """Apply deterministic local reranking to enriched discovery candidates."""

    ranked = sorted(
        candidates,
        key=lambda candidate: _ranking_key(intent, candidate, selection_preferences),
        reverse=True,
    )
    return [
        replace(candidate, ranking_position=index)
        for index, candidate in enumerate(ranked, start=1)
    ]


def _ranking_key(
    intent: SearchIntent,
    candidate: DiscoveryCandidate,
    selection_preferences: SelectionPreferences,
) -> tuple[object, ...]:
    version = candidate.selected_version
    labels = set(candidate.labels)
    query_labels = set(intent.preferred_labels)

    normalized_name = normalize_text(version.name)
    exact_name_match = int(normalized_name == intent.normalized_query)
    exact_slug_match = int(candidate.slug == intent.normalized_query.replace(" ", "."))
    runtime = version.headers.get("runtime")
    runtime_match = int(intent.language is not None and runtime == intent.language)
    matched_labels = len(query_labels.intersection(labels))
    matched_tags = len(query_labels.intersection(set(version.tags)))
    description_terms = set(normalize_text(version.description).split())
    matched_description_terms = len(query_labels.intersection(description_terms))
    preferred_trust = int(
        intent.trust_preference is not None and version.trust_tier == intent.trust_preference
    )
    token_known, token_score = _cost_key(version.token_estimate)
    size_known, size_score = _cost_key(version.content_size_bytes)
    current_default = int(version.is_current_default)
    trust_rank = trust_tier_rank(version.trust_tier)
    lifecycle_rank = lifecycle_status_rank(version.lifecycle_status)
    relevance = (
        exact_name_match,
        exact_slug_match,
        runtime_match,
        matched_tags,
        matched_labels,
        matched_description_terms,
        preferred_trust,
    )
    freshness = (
        current_default,
        Version(version.coordinate.version),
        version.published_at,
        candidate.slug,
    )

    if selection_preferences.profile == "low-cost":
        return (
            *relevance,
            token_known,
            token_score,
            size_known,
            size_score,
            trust_rank,
            lifecycle_rank,
            *freshness,
            "".join(candidate.match_reasons),
        )

    if selection_preferences.profile == "high-trust":
        return (
            *relevance,
            trust_rank,
            lifecycle_rank,
            token_known,
            token_score,
            size_known,
            size_score,
            *freshness,
            "".join(candidate.match_reasons),
        )

    return (
        *relevance,
        trust_rank,
        token_known,
        token_score,
        size_known,
        size_score,
        lifecycle_rank,
        *freshness,
        "".join(candidate.match_reasons),
    )


def _cost_key(value: int | None) -> tuple[int, int]:
    if value is None:
        return (0, 0)
    return (1, -value)
