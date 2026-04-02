"""Resolver-owned candidate version selection for discovered skills."""

from __future__ import annotations

import re
from typing import Protocol

from aptitude_resolver.domain.errors import SkillNotFoundError
from aptitude_resolver.domain.models import (
    DiscoveredSkill,
    DiscoveryCandidate,
    SearchIntent,
    SkillMetadata,
    VersionSummary,
)
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.resolution.solver.version_selection import (
    select_preferred_version,
)


WORD_RE = re.compile(r"[A-Za-z0-9._-]+")


class RegistryCandidateVersionPort(Protocol):
    """Registry reads required for resolver-owned candidate version resolution."""

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata: ...


def resolve_candidate_versions(
    intent: SearchIntent,
    matches: list[DiscoveredSkill],
    registry_client: RegistryCandidateVersionPort,
    *,
    version: str | None = None,
) -> tuple[list[DiscoveryCandidate], list[TraceEntry]]:
    """Select one concrete version for each discovered skill."""

    candidates: list[DiscoveryCandidate] = []
    trace: list[TraceEntry] = []

    for match in matches:
        selected_version, selection_trace = _select_candidate_version(
            intent=intent,
            match=match,
            registry_client=registry_client,
            version=version,
        )
        trace.extend(selection_trace)
        if selected_version is None:
            continue

        labels = _derive_labels(selected_version)
        matched_labels = [label for label in intent.preferred_labels if label in labels]
        reasons: list[str] = []
        if _normalize_text(selected_version.name) == intent.normalized_query:
            reasons.append("exact_name_match")
        if match.slug == intent.normalized_query.replace(" ", "."):
            reasons.append("exact_slug_match")
        if (
            intent.language
            and selected_version.headers.get("runtime") == intent.language
        ):
            reasons.append("runtime_match")
        if matched_labels:
            reasons.append("label_overlap")
        if not reasons:
            reasons.append("server_candidate")

        candidates.append(
            DiscoveryCandidate(
                slug=match.slug,
                selected_version=selected_version,
                labels=labels,
                matched_labels=matched_labels,
                match_reasons=reasons,
            )
        )

    return candidates, trace


def _select_candidate_version(
    *,
    intent: SearchIntent,
    match: DiscoveredSkill,
    registry_client: RegistryCandidateVersionPort,
    version: str | None,
) -> tuple[VersionSummary | None, list[TraceEntry]]:
    trace: list[TraceEntry] = []

    if version is not None:
        try:
            metadata = registry_client.fetch_skill_metadata(match.slug, version)
        except SkillNotFoundError:
            trace.append(
                TraceEntry(
                    stage="resolver",
                    action="candidate_version_miss",
                    message=(
                        f"Discovered candidate {match.slug} did not expose requested version {version}."
                    ),
                    data={"slug": match.slug, "requested_version": version},
                )
            )
            return None, trace

        selected_version = _version_summary_from_metadata(metadata)
        trace.append(
            TraceEntry(
                stage="resolver",
                action="select_candidate_version",
                message=f"Selected requested version {version} for candidate {match.slug}.",
                data={
                    "slug": match.slug,
                    "version": version,
                    "selection_source": "requested_version",
                    "intent_terms": list(intent.terms),
                },
            )
        )
        return selected_version, trace

    selected_version = select_preferred_version(match.available_versions)
    trace.append(
        TraceEntry(
            stage="resolver",
            action="select_candidate_version",
            message=(
                f"Selected preferred version {selected_version.coordinate.version} for candidate {match.slug}."
            ),
            data={
                "slug": match.slug,
                "version": selected_version.coordinate.version,
                "selection_source": "preferred_version",
                "version_count": len(match.available_versions),
                "intent_terms": list(intent.terms),
            },
        )
    )

    if _requires_metadata_enrichment(selected_version):
        metadata = registry_client.fetch_skill_metadata(
            match.slug,
            selected_version.coordinate.version,
        )
        selected_version = _merge_enriched_version(selected_version, metadata)
        trace.append(
            TraceEntry(
                stage="resolver",
                action="enrich_candidate_version",
                message=(
                    f"Enriched candidate {match.slug}@{selected_version.coordinate.version} with exact metadata."
                ),
                data={
                    "slug": match.slug,
                    "version": selected_version.coordinate.version,
                },
            )
        )

    return selected_version, trace


def _version_summary_from_metadata(metadata: SkillMetadata) -> VersionSummary:
    return VersionSummary(
        coordinate=metadata.coordinate,
        name=metadata.name,
        description=metadata.description,
        tags=list(metadata.tags),
        headers=dict(metadata.headers),
        rendered_summary=metadata.rendered_summary,
        lifecycle_status=metadata.lifecycle_status,
        trust_tier=metadata.trust_tier,
        published_at=metadata.published_at,
        content_checksum_algorithm=metadata.content_checksum_algorithm,
        content_checksum_digest=metadata.content_checksum_digest,
        content_size_bytes=metadata.content_size_bytes,
        token_estimate=metadata.token_estimate,
        maturity_score=metadata.maturity_score,
        security_score=metadata.security_score,
    )


def _merge_enriched_version(
    version: VersionSummary, metadata: SkillMetadata
) -> VersionSummary:
    return VersionSummary(
        coordinate=metadata.coordinate,
        name=metadata.name,
        description=metadata.description,
        tags=list(metadata.tags),
        headers=dict(metadata.headers),
        rendered_summary=metadata.rendered_summary,
        lifecycle_status=version.lifecycle_status,
        trust_tier=version.trust_tier,
        published_at=version.published_at,
        content_checksum_algorithm=metadata.content_checksum_algorithm,
        content_checksum_digest=metadata.content_checksum_digest,
        content_size_bytes=metadata.content_size_bytes,
        token_estimate=metadata.token_estimate,
        maturity_score=metadata.maturity_score,
        security_score=metadata.security_score,
        is_current_default=version.is_current_default,
    )


def _derive_labels(version: VersionSummary) -> list[str]:
    derived = list(version.tags)
    runtime = version.headers.get("runtime")
    if runtime:
        derived.append(runtime)
    derived.extend(_normalize_text(version.name).split())
    derived.extend(_normalize_text(version.description).split())
    return list(dict.fromkeys(label for label in derived if label))


def _requires_metadata_enrichment(version: VersionSummary) -> bool:
    return not (
        version.name
        and version.description
        and version.rendered_summary
        and version.tags
        and version.headers
    )


def _normalize_text(value: str) -> str:
    return " ".join(WORD_RE.findall(value.lower()))
