"""Minimal deterministic result shaping for exact-coordinate reads."""

from __future__ import annotations

from aptitude_client.application.dto import (
    ResolveCoordinateDto,
    ResolveDependencyDto,
    ResolveRequestDto,
    ResolveResultDto,
    ResolveSkillSummaryDto,
)
from aptitude_client.domain.models import DependencySpec, SkillMetadata


def shape_exact_resolve_result(
    request: ResolveRequestDto,
    metadata: SkillMetadata,
    dependencies: list[DependencySpec],
) -> ResolveResultDto:
    """Convert exact metadata plus direct dependencies into a stable result DTO."""

    return ResolveResultDto(
        requested_coordinate=ResolveCoordinateDto(
            slug=request.slug,
            version=request.version,
        ),
        selected_coordinate=ResolveCoordinateDto(
            slug=metadata.coordinate.slug,
            version=metadata.coordinate.version,
        ),
        skill=ResolveSkillSummaryDto(
            name=metadata.name,
            description=metadata.description,
            tags=list(metadata.tags),
            rendered_summary=metadata.rendered_summary,
            lifecycle_status=metadata.lifecycle_status,
            trust_tier=metadata.trust_tier,
        ),
        dependencies=[
            ResolveDependencyDto(
                slug=dependency.slug,
                version=dependency.version,
                optional=dependency.optional,
                markers=list(dependency.markers),
            )
            for dependency in dependencies
        ],
    )
