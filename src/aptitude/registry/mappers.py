"""Mapping helpers from registry transport models to domain models."""

from __future__ import annotations

from aptitude.domain.models import (
    DependencySpec,
    SkillCoordinate,
    SkillMetadata,
    VersionSummary,
)
from aptitude.registry.transport_models import (
    DependencySelector,
    DirectDependenciesResponse,
    MetadataResponse,
    SkillVersionListResponse,
)


def map_metadata_response(payload: MetadataResponse) -> SkillMetadata:
    """Map exact metadata transport payloads into domain models."""

    return SkillMetadata(
        coordinate=SkillCoordinate(slug=payload.slug, version=payload.version),
        name=payload.metadata.name,
        description=payload.metadata.description,
        tags=list(payload.metadata.tags),
        headers={
            str(key): str(value)
            for key, value in payload.metadata.headers.items()
            if value is not None
        },
        inputs_schema=payload.metadata.inputs_schema,
        outputs_schema=payload.metadata.outputs_schema,
        token_estimate=payload.metadata.token_estimate,
        maturity_score=payload.metadata.maturity_score,
        security_score=payload.metadata.security_score,
        rendered_summary=(
            payload.content.rendered_summary
            or payload.metadata.description
            or payload.metadata.name
        ),
        content_checksum_algorithm=payload.content.checksum.algorithm,
        content_checksum_digest=payload.content.checksum.digest,
        content_size_bytes=payload.content.size_bytes,
        lifecycle_status=payload.lifecycle_status,
        trust_tier=payload.trust_tier,
        published_at=payload.published_at,
    )


def map_version_summary(payload: MetadataResponse) -> VersionSummary:
    """Map one metadata payload into a version summary."""

    metadata = map_metadata_response(payload)
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


def map_skill_version_list_response(
    payload: SkillVersionListResponse,
) -> list[VersionSummary]:
    """Map version list transport payloads into version summaries."""

    return [
        VersionSummary(
            coordinate=SkillCoordinate(slug=payload.slug, version=item.version),
            lifecycle_status=item.lifecycle_status or "published",
            trust_tier=item.trust_tier or "untrusted",
            published_at=item.published_at or "",
            is_current_default=item.is_current_default,
        )
        for item in payload.versions
    ]


def map_direct_dependencies(
    payload: DirectDependenciesResponse,
) -> list[DependencySpec]:
    """Map direct dependency transport payloads into domain models."""

    return [map_dependency_selector(item) for item in payload.depends_on]


def map_dependency_selector(payload: DependencySelector) -> DependencySpec:
    """Map one dependency selector into a resolver-owned domain model."""

    return DependencySpec(
        slug=payload.slug,
        version=payload.version,
        version_constraint=payload.version_constraint,
        optional=payload.optional,
        markers=list(payload.markers),
    )
