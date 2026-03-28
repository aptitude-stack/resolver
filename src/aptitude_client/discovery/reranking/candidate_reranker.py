"""Deterministic client-side discovery reranking."""

from __future__ import annotations

from dataclasses import replace

from packaging.version import Version

from aptitude_client.discovery.intent import normalize_text
from aptitude_client.domain.models import DiscoveryCandidate, SearchIntent


TRUST_RANK = {"verified": 2, "internal": 1, "untrusted": 0}
LIFECYCLE_RANK = {"published": 2, "deprecated": 1, "archived": 0}


def rerank_candidates(
    intent: SearchIntent,
    candidates: list[DiscoveryCandidate],
) -> list[DiscoveryCandidate]:
    """Apply deterministic local reranking to enriched discovery candidates."""

    ranked = sorted(candidates, key=lambda candidate: _ranking_key(intent, candidate), reverse=True)
    return [
        replace(candidate, ranking_position=index)
        for index, candidate in enumerate(ranked, start=1)
    ]


def _ranking_key(intent: SearchIntent, candidate: DiscoveryCandidate) -> tuple[object, ...]:
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

    return (
        exact_name_match,
        exact_slug_match,
        runtime_match,
        matched_tags,
        matched_labels,
        matched_description_terms,
        preferred_trust,
        TRUST_RANK.get(version.trust_tier, -1),
        LIFECYCLE_RANK.get(version.lifecycle_status, -1),
        Version(version.coordinate.version),
        version.published_at,
        "".join(candidate.match_reasons),
        candidate.slug,
    )
