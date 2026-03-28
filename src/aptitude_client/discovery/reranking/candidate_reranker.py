"""Deterministic client-side discovery reranking."""

from __future__ import annotations

from dataclasses import dataclass
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
        (
            (candidate, _ranking_components(intent, candidate))
            for candidate in candidates
        ),
        key=lambda item: item[1].sort_key(selection_preferences.profile),
        reverse=True,
    )
    ranked_candidates = [item[0] for item in ranked]
    ranked_components = [item[1] for item in ranked]
    varying_fields = _varying_prompt_fields(ranked_candidates)
    return [
        replace(
            candidate,
            ranking_position=index,
            selection_details=_selection_details(candidate, varying_fields),
            selection_reason=_selection_reason(
                candidate,
                current_components=components,
                next_candidate=ranked_candidates[index] if index < len(ranked_candidates) else None,
                next_components=ranked_components[index] if index < len(ranked_components) else None,
                profile=selection_preferences.profile,
            ),
        )
        for index, (candidate, components) in enumerate(
            zip(ranked_candidates, ranked_components, strict=False),
            start=1,
        )
    ]


@dataclass(frozen=True)
class RankingComponents:
    """Comparable ranking components for one candidate."""

    exact_name_match: int
    exact_slug_match: int
    runtime_match: int
    matched_tags: int
    matched_labels: int
    matched_description_terms: int
    preferred_trust: int
    trust_rank: int
    lifecycle_rank: int
    token_known: int
    token_score: int
    size_known: int
    size_score: int
    current_default: int
    semantic_version: Version
    published_at: str
    slug: str
    match_reasons: str

    def sort_key(self, profile: str) -> tuple[object, ...]:
        """Return the deterministic sort key for one ranking profile."""

        relevance = (
            self.exact_name_match,
            self.exact_slug_match,
            self.runtime_match,
            self.matched_tags,
            self.matched_labels,
            self.matched_description_terms,
            self.preferred_trust,
        )
        freshness = (
            self.current_default,
            self.semantic_version,
            self.published_at,
            self.slug,
        )

        if profile == "low-cost":
            return (
                *relevance,
                self.token_known,
                self.token_score,
                self.size_known,
                self.size_score,
                self.trust_rank,
                self.lifecycle_rank,
                *freshness,
                self.match_reasons,
            )

        if profile == "high-trust":
            return (
                *relevance,
                self.trust_rank,
                self.lifecycle_rank,
                self.token_known,
                self.token_score,
                self.size_known,
                self.size_score,
                *freshness,
                self.match_reasons,
            )

        return (
            *relevance,
            self.trust_rank,
            self.token_known,
            self.token_score,
            self.size_known,
            self.size_score,
            self.lifecycle_rank,
            *freshness,
            self.match_reasons,
        )


def _ranking_components(
    intent: SearchIntent,
    candidate: DiscoveryCandidate,
) -> RankingComponents:
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
    return RankingComponents(
        exact_name_match=exact_name_match,
        exact_slug_match=exact_slug_match,
        runtime_match=runtime_match,
        matched_tags=matched_tags,
        matched_labels=matched_labels,
        matched_description_terms=matched_description_terms,
        preferred_trust=preferred_trust,
        trust_rank=trust_rank,
        lifecycle_rank=lifecycle_rank,
        token_known=token_known,
        token_score=token_score,
        size_known=size_known,
        size_score=size_score,
        current_default=current_default,
        semantic_version=Version(version.coordinate.version),
        published_at=version.published_at,
        slug=candidate.slug,
        match_reasons="".join(candidate.match_reasons),
    )


def _cost_key(value: int | None) -> tuple[int, int]:
    if value is None:
        return (0, 0)
    return (1, -value)


def _varying_prompt_fields(candidates: list[DiscoveryCandidate]) -> set[str]:
    """Return candidate fields worth surfacing during interactive ambiguity."""

    fields: dict[str, set[object]] = {
        "published_at": {candidate.selected_version.published_at for candidate in candidates},
        "token_estimate": {candidate.selected_version.token_estimate for candidate in candidates},
        "content_size_bytes": {
            candidate.selected_version.content_size_bytes for candidate in candidates
        },
    }
    return {
        field_name
        for field_name, values in fields.items()
        if len(values) > 1 or (field_name in {"token_estimate", "content_size_bytes"} and None not in values)
    }


def _selection_details(
    candidate: DiscoveryCandidate,
    varying_fields: set[str],
) -> list[str]:
    """Build human-readable candidate details for interactive prompting."""

    version = candidate.selected_version
    details: list[str] = []

    if "token_estimate" in varying_fields:
        details.append(
            f"tokens={version.token_estimate}" if version.token_estimate is not None else "tokens=unknown"
        )
    if "content_size_bytes" in varying_fields:
        details.append(
            (
                f"size={version.content_size_bytes}B"
                if version.content_size_bytes is not None
                else "size=unknown"
            )
        )
    if "published_at" in varying_fields:
        details.append(f"published={version.published_at}")

    return details


def _selection_reason(
    candidate: DiscoveryCandidate,
    *,
    current_components: RankingComponents,
    next_candidate: DiscoveryCandidate | None,
    next_components: RankingComponents | None,
    profile: str,
) -> str | None:
    """Explain why one ranked candidate stayed ahead of the next candidate."""

    if next_candidate is None or next_components is None:
        return None

    reason = _comparison_reason(current_components, next_components, profile)
    if reason is None:
        return None

    return (
        f"ranked above {next_candidate.slug}@{next_candidate.selected_coordinate.version}: "
        f"{reason}"
    )


def _comparison_reason(
    current: RankingComponents,
    next_item: RankingComponents,
    profile: str,
) -> str | None:
    """Return the first decisive reason that kept one candidate ahead of the next."""

    if profile == "low-cost":
        comparisons = (
            ("exact_name_match", current.exact_name_match, next_item.exact_name_match, "closer exact name match"),
            ("exact_slug_match", current.exact_slug_match, next_item.exact_slug_match, "closer exact slug match"),
            ("runtime_match", current.runtime_match, next_item.runtime_match, "better runtime match"),
            ("matched_tags", current.matched_tags, next_item.matched_tags, "stronger tag match"),
            ("matched_labels", current.matched_labels, next_item.matched_labels, "stronger label match"),
            (
                "matched_description_terms",
                current.matched_description_terms,
                next_item.matched_description_terms,
                "stronger description match",
            ),
            ("preferred_trust", current.preferred_trust, next_item.preferred_trust, "matches requested trust preference"),
            ("token_known", current.token_known, next_item.token_known, "known token estimate"),
            ("token_score", current.token_score, next_item.token_score, "lower token estimate"),
            ("size_known", current.size_known, next_item.size_known, "known content size"),
            ("size_score", current.size_score, next_item.size_score, "smaller content size"),
            ("trust_rank", current.trust_rank, next_item.trust_rank, "higher trust tier"),
            ("lifecycle_rank", current.lifecycle_rank, next_item.lifecycle_rank, "better lifecycle status"),
            ("current_default", current.current_default, next_item.current_default, "current default version"),
            ("semantic_version", current.semantic_version, next_item.semantic_version, "newer semantic version"),
            ("published_at", current.published_at, next_item.published_at, "newer publication date"),
            ("slug", current.slug, next_item.slug, "stable slug tiebreak"),
        )
    elif profile == "high-trust":
        comparisons = (
            ("exact_name_match", current.exact_name_match, next_item.exact_name_match, "closer exact name match"),
            ("exact_slug_match", current.exact_slug_match, next_item.exact_slug_match, "closer exact slug match"),
            ("runtime_match", current.runtime_match, next_item.runtime_match, "better runtime match"),
            ("matched_tags", current.matched_tags, next_item.matched_tags, "stronger tag match"),
            ("matched_labels", current.matched_labels, next_item.matched_labels, "stronger label match"),
            (
                "matched_description_terms",
                current.matched_description_terms,
                next_item.matched_description_terms,
                "stronger description match",
            ),
            ("preferred_trust", current.preferred_trust, next_item.preferred_trust, "matches requested trust preference"),
            ("trust_rank", current.trust_rank, next_item.trust_rank, "higher trust tier"),
            ("lifecycle_rank", current.lifecycle_rank, next_item.lifecycle_rank, "better lifecycle status"),
            ("token_known", current.token_known, next_item.token_known, "known token estimate"),
            ("token_score", current.token_score, next_item.token_score, "lower token estimate"),
            ("size_known", current.size_known, next_item.size_known, "known content size"),
            ("size_score", current.size_score, next_item.size_score, "smaller content size"),
            ("current_default", current.current_default, next_item.current_default, "current default version"),
            ("semantic_version", current.semantic_version, next_item.semantic_version, "newer semantic version"),
            ("published_at", current.published_at, next_item.published_at, "newer publication date"),
            ("slug", current.slug, next_item.slug, "stable slug tiebreak"),
        )
    else:
        comparisons = (
            ("exact_name_match", current.exact_name_match, next_item.exact_name_match, "closer exact name match"),
            ("exact_slug_match", current.exact_slug_match, next_item.exact_slug_match, "closer exact slug match"),
            ("runtime_match", current.runtime_match, next_item.runtime_match, "better runtime match"),
            ("matched_tags", current.matched_tags, next_item.matched_tags, "stronger tag match"),
            ("matched_labels", current.matched_labels, next_item.matched_labels, "stronger label match"),
            (
                "matched_description_terms",
                current.matched_description_terms,
                next_item.matched_description_terms,
                "stronger description match",
            ),
            ("preferred_trust", current.preferred_trust, next_item.preferred_trust, "matches requested trust preference"),
            ("trust_rank", current.trust_rank, next_item.trust_rank, "higher trust tier"),
            ("token_known", current.token_known, next_item.token_known, "known token estimate"),
            ("token_score", current.token_score, next_item.token_score, "lower token estimate"),
            ("size_known", current.size_known, next_item.size_known, "known content size"),
            ("size_score", current.size_score, next_item.size_score, "smaller content size"),
            ("lifecycle_rank", current.lifecycle_rank, next_item.lifecycle_rank, "better lifecycle status"),
            ("current_default", current.current_default, next_item.current_default, "current default version"),
            ("semantic_version", current.semantic_version, next_item.semantic_version, "newer semantic version"),
            ("published_at", current.published_at, next_item.published_at, "newer publication date"),
            ("slug", current.slug, next_item.slug, "stable slug tiebreak"),
        )

    for _, current_value, next_value, reason in comparisons:
        if current_value != next_value:
            return reason
    return None
