"""Mapping helpers from registry transport models to domain models."""

from __future__ import annotations

from aptitude_client.domain.models import DependencySpec, SkillCoordinate, SkillMetadata
from aptitude_client.registry.transport_models import (
    DependencySelector,
    DirectDependenciesResponse,
    MetadataResponse,
)


def map_metadata_response(payload: MetadataResponse) -> SkillMetadata:
    """Map exact metadata transport payloads into domain models."""

    return SkillMetadata(
        coordinate=SkillCoordinate(slug=payload.slug, version=payload.version),
        name=payload.metadata.name,
        description=payload.metadata.description,
        tags=list(payload.metadata.tags),
        rendered_summary=payload.content.rendered_summary,
        content_checksum_algorithm=payload.content.checksum.algorithm,
        content_checksum_digest=payload.content.checksum.digest,
        lifecycle_status=payload.lifecycle_status,
        trust_tier=payload.trust_tier,
        published_at=payload.published_at,
    )


def map_direct_dependencies(payload: DirectDependenciesResponse) -> list[DependencySpec]:
    """Map direct dependency transport payloads into domain models."""

    return [map_dependency_selector(item) for item in payload.depends_on]


def map_dependency_selector(payload: DependencySelector) -> DependencySpec:
    """Map one dependency selector into a client-owned domain model."""

    return DependencySpec(
        slug=payload.slug,
        version=payload.version,
        optional=payload.optional,
        markers=list(payload.markers),
    )
