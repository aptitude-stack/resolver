"""Internal mapping helpers for planned resolution artifacts and DTOs."""

from __future__ import annotations

from aptitude_client.application.dto import (
    ConflictDto,
    DiscoveryCandidateDto,
    ExecutionPlanDto,
    ExecutionStepDto,
    GovernanceSnapshotDto,
    LockedEdgeDto,
    LockedSkillDto,
    LockfileDto,
    LockRootDto,
    PolicySnapshotDto,
    PolicyEvaluationDto,
    ResolvedEdgeDto,
    ResolvedGraphDto,
    ResolvedSkillNodeDto,
    ResolveCoordinateDto,
    ResolveSkillSummaryDto,
    SelectionSnapshotDto,
    TraceEntryDto,
)
from aptitude_client.execution import ExecutionPlan
from aptitude_client.application.queries.plan_skill_resolution import ResolutionArtifact
from aptitude_client.domain.models import DiscoveryCandidate, ResolutionGraph
from aptitude_client.domain.policy import PolicyEvaluation
from aptitude_client.domain.tracing import TraceEntry
from aptitude_client.lockfile import Lockfile


def candidate_to_dto(candidate: DiscoveryCandidate) -> DiscoveryCandidateDto:
    """Map one internal discovery candidate to a client-facing DTO."""

    version = candidate.selected_version
    return DiscoveryCandidateDto(
        slug=candidate.slug,
        version=version.coordinate.version,
        name=version.name,
        description=version.description,
        tags=list(version.tags),
        labels=list(candidate.labels),
        matched_labels=list(candidate.matched_labels),
        match_reasons=list(candidate.match_reasons),
        runtime=version.headers.get("runtime"),
        lifecycle_status=version.lifecycle_status,
        trust_tier=version.trust_tier,
        token_estimate=version.token_estimate,
        content_size_bytes=version.content_size_bytes,
        published_at=version.published_at,
        ranking_position=candidate.ranking_position or 0,
        selection_details=list(candidate.selection_details),
        selection_reason=candidate.selection_reason,
    )


def graph_to_dto(graph: ResolutionGraph) -> ResolvedGraphDto:
    """Map one resolved graph into a client-facing graph DTO."""

    return ResolvedGraphDto(
        root=ResolveCoordinateDto(slug=graph.root.slug, version=graph.root.version),
        nodes=[
            ResolvedSkillNodeDto(
                slug=node.coordinate.slug,
                version=node.coordinate.version,
                name=node.name,
                description=node.description,
                tags=list(node.tags),
                runtime=node.headers.get("runtime"),
                rendered_summary=node.rendered_summary,
                lifecycle_status=node.lifecycle_status,
                trust_tier=node.trust_tier,
                published_at=node.published_at,
            )
            for node in graph.nodes
        ],
        edges=[
            ResolvedEdgeDto(
                source=ResolveCoordinateDto(
                    slug=edge.source.slug, version=edge.source.version
                ),
                target=ResolveCoordinateDto(
                    slug=edge.target.slug, version=edge.target.version
                ),
                edge_type=edge.edge_type,
                optional=edge.optional,
                markers=list(edge.markers),
            )
            for edge in graph.edges
        ],
        install_order=[
            ResolveCoordinateDto(slug=coordinate.slug, version=coordinate.version)
            for coordinate in graph.install_order
        ],
        conflicts=[
            ConflictDto(
                code=conflict.code,
                message=conflict.message,
                coordinates=[
                    ResolveCoordinateDto(slug=item.slug, version=item.version)
                    for item in conflict.coordinates
                ],
            )
            for conflict in graph.conflicts
        ],
    )


def lockfile_to_dto(lockfile: Lockfile) -> LockfileDto:
    """Map one lockfile dataclass to its DTO representation."""

    return LockfileDto(
        version=lockfile.version,
        generated_at=lockfile.generated_at,
        client_version=lockfile.client_version,
        root=LockRootDto(
            request=lockfile.root.request,
            requested_version=lockfile.root.requested_version,
            selected_node_id=lockfile.root.selected_node_id,
            selection_mode=lockfile.root.selection_mode,
        ),
        nodes=[
            LockedSkillDto(
                node_id=node.node_id,
                slug=node.slug,
                version=node.version,
                artifact_ref=node.artifact_ref,
                name=node.name,
                description=node.description,
                tags=list(node.tags),
                headers=dict(node.headers),
                rendered_summary=node.rendered_summary,
                lifecycle_status=node.lifecycle_status,
                trust_tier=node.trust_tier,
                published_at=node.published_at,
                content_checksum={
                    "algorithm": node.content_checksum_algorithm,
                    "digest": node.content_checksum_digest,
                    "size_bytes": node.content_size_bytes,
                },
            )
            for node in lockfile.nodes
        ],
        edges=[
            LockedEdgeDto(
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                edge_type=edge.edge_type,
                optional=edge.optional,
                markers=list(edge.markers),
            )
            for edge in lockfile.edges
        ],
        install_order=list(lockfile.install_order),
        selection=(
            SelectionSnapshotDto(
                profile=lockfile.selection.profile,
                interaction_mode=lockfile.selection.interaction_mode,
                profile_source=lockfile.selection.profile_source,
                interaction_mode_source=lockfile.selection.interaction_mode_source,
            )
            if lockfile.selection is not None
            else None
        ),
        policy=(
            PolicySnapshotDto(
                profile=lockfile.policy.profile,
                source=lockfile.policy.source,
                allowed_lifecycle_statuses=list(
                    lockfile.policy.allowed_lifecycle_statuses
                ),
                allowed_trust_tiers=list(lockfile.policy.allowed_trust_tiers),
                max_token_estimate=lockfile.policy.max_token_estimate,
                max_content_size_bytes=lockfile.policy.max_content_size_bytes,
                max_total_token_estimate=lockfile.policy.max_total_token_estimate,
                max_total_content_size_bytes=lockfile.policy.max_total_content_size_bytes,
            )
            if lockfile.policy is not None
            else None
        ),
        governance=[
            GovernanceSnapshotDto(
                rule=item.rule,
                passed=item.passed,
                message=item.message,
                node_id=item.node_id,
            )
            for item in lockfile.governance
        ],
    )


def execution_plan_to_dto(execution_plan: ExecutionPlan) -> ExecutionPlanDto:
    """Map one execution plan dataclass to its DTO representation."""

    return ExecutionPlanDto(
        steps=[
            ExecutionStepDto(
                node_id=step.node_id,
                skill=step.skill,
                version=step.version,
                artifact_ref=step.artifact_ref,
                action=step.action,
            )
            for step in execution_plan.steps
        ]
    )


def trace_to_dto(entry: TraceEntry) -> TraceEntryDto:
    """Map one trace entry to its DTO representation."""

    return TraceEntryDto(
        stage=entry.stage,
        action=entry.action,
        message=entry.message,
        data=dict(entry.data),
    )


def policy_to_dto(evaluation: PolicyEvaluation) -> PolicyEvaluationDto:
    """Map one policy evaluation to a client-facing DTO."""

    coordinate = None
    if evaluation.coordinate is not None:
        coordinate = ResolveCoordinateDto(
            slug=evaluation.coordinate.slug,
            version=evaluation.coordinate.version,
        )

    return PolicyEvaluationDto(
        rule=evaluation.rule,
        passed=evaluation.passed,
        message=evaluation.message,
        coordinate=coordinate,
    )


def selected_skill_to_dto(artifact: ResolutionArtifact) -> ResolveSkillSummaryDto:
    """Map the root selected node from one artifact to a skill summary DTO."""

    root_node = next(
        node
        for node in artifact.graph.nodes
        if node.coordinate.slug == artifact.graph.root.slug
        and node.coordinate.version == artifact.graph.root.version
    )
    return ResolveSkillSummaryDto(
        name=root_node.name,
        description=root_node.description,
        tags=list(root_node.tags),
        runtime=root_node.headers.get("runtime"),
        rendered_summary=root_node.rendered_summary,
        lifecycle_status=root_node.lifecycle_status,
        trust_tier=root_node.trust_tier,
    )
