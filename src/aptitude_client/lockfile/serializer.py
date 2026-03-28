"""Lockfile build and serialization helpers."""

from __future__ import annotations

import json

from aptitude_client.domain.models import ResolutionGraph
from aptitude_client.domain.policy import PolicyContext, PolicyEvaluation, SelectionPreferences
from aptitude_client.lockfile.model import (
    GovernanceSnapshotEntry,
    LockRoot,
    Lockfile,
    LockedEdge,
    LockedSkill,
    PolicySnapshot,
    SelectionSnapshot,
)


def build_lockfile(
    *,
    graph: ResolutionGraph,
    requested_query: str,
    requested_version: str | None,
    selection_mode: str,
    policy_evaluations: list[PolicyEvaluation],
    policy_context: PolicyContext | None = None,
    selection_preferences: SelectionPreferences | None = None,
    client_version: str | None = None,
) -> Lockfile:
    """Build a deterministic lock artifact from one resolved graph."""

    nodes = sorted(
        (
            LockedSkill(
                node_id=_node_id(node.coordinate.slug, node.coordinate.version),
                slug=node.coordinate.slug,
                version=node.coordinate.version,
                artifact_ref=_artifact_ref(node.coordinate.slug, node.coordinate.version),
                name=node.name,
                description=node.description,
                tags=sorted(node.tags),
                headers={key: node.headers[key] for key in sorted(node.headers)},
                rendered_summary=node.rendered_summary,
                lifecycle_status=node.lifecycle_status,
                trust_tier=node.trust_tier,
                published_at=node.published_at,
                content_checksum_algorithm=node.content_checksum_algorithm,
                content_checksum_digest=node.content_checksum_digest,
                content_size_bytes=node.content_size_bytes,
            )
            for node in graph.nodes
        ),
        key=lambda item: item.node_id,
    )
    edges = sorted(
        (
            LockedEdge(
                source_node_id=_node_id(edge.source.slug, edge.source.version),
                target_node_id=_node_id(edge.target.slug, edge.target.version),
                edge_type=edge.edge_type,
                optional=edge.optional,
                markers=sorted(edge.markers),
            )
            for edge in graph.edges
        ),
        key=lambda item: (
            item.source_node_id,
            item.target_node_id,
            item.edge_type,
            item.optional,
            tuple(item.markers),
        ),
    )
    governance = sorted(
        (
            GovernanceSnapshotEntry(
                rule=evaluation.rule,
                passed=evaluation.passed,
                message=evaluation.message,
                node_id=(
                    _node_id(evaluation.coordinate.slug, evaluation.coordinate.version)
                    if evaluation.coordinate is not None
                    else None
                ),
            )
            for evaluation in policy_evaluations
        ),
        key=lambda item: (
            item.rule,
            item.node_id or "",
            item.message,
            item.passed,
        ),
    )
    install_order = [
        _node_id(coordinate.slug, coordinate.version)
        for coordinate in graph.install_order
    ]

    published_timestamps = sorted(node.published_at for node in nodes if node.published_at)
    generated_at = published_timestamps[-1] if published_timestamps else None
    effective_policy = policy_context or PolicyContext()

    return Lockfile(
        version=1,
        generated_at=generated_at,
        client_version=client_version,
        root=LockRoot(
            request=requested_query,
            requested_version=requested_version,
            selected_node_id=_node_id(graph.root.slug, graph.root.version),
            selection_mode=selection_mode,
        ),
        nodes=nodes,
        edges=edges,
        install_order=install_order,
        selection=(
            SelectionSnapshot(
                profile=selection_preferences.profile,
                interaction_mode=selection_preferences.interaction_mode,
                profile_source=selection_preferences.profile_source,
                interaction_mode_source=selection_preferences.interaction_mode_source,
            )
            if selection_preferences is not None
            else None
        ),
        policy=PolicySnapshot(
            profile=effective_policy.profile,
            source=effective_policy.source,
            allowed_lifecycle_statuses=list(effective_policy.allowed_lifecycle_statuses),
            allowed_trust_tiers=list(effective_policy.allowed_trust_tiers),
            max_token_estimate=effective_policy.max_token_estimate,
            max_content_size_bytes=effective_policy.max_content_size_bytes,
            max_total_token_estimate=effective_policy.max_total_token_estimate,
            max_total_content_size_bytes=effective_policy.max_total_content_size_bytes,
        ),
        governance=governance,
    )


def serialize_lockfile(lockfile: Lockfile) -> str:
    """Serialize one lockfile to deterministic JSON."""

    return json.dumps(lockfile_to_dict(lockfile), indent=2)


def lockfile_to_dict(lockfile: Lockfile) -> dict[str, object]:
    """Convert one lockfile dataclass to a JSON-safe mapping."""

    return {
        "version": lockfile.version,
        "generated_at": lockfile.generated_at,
        "client_version": lockfile.client_version,
        "root": {
            "request": lockfile.root.request,
            "requested_version": lockfile.root.requested_version,
            "selected_node_id": lockfile.root.selected_node_id,
            "selection_mode": lockfile.root.selection_mode,
        },
        "nodes": [
            {
                "node_id": node.node_id,
                "slug": node.slug,
                "version": node.version,
                "artifact_ref": node.artifact_ref,
                "name": node.name,
                "description": node.description,
                "tags": list(node.tags),
                "headers": dict(node.headers),
                "rendered_summary": node.rendered_summary,
                "lifecycle_status": node.lifecycle_status,
                "trust_tier": node.trust_tier,
                "published_at": node.published_at,
                "content_checksum": {
                    "algorithm": node.content_checksum_algorithm,
                    "digest": node.content_checksum_digest,
                    "size_bytes": node.content_size_bytes,
                },
            }
            for node in lockfile.nodes
        ],
        "edges": [
            {
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "edge_type": edge.edge_type,
                "optional": edge.optional,
                "markers": list(edge.markers),
            }
            for edge in lockfile.edges
        ],
        "install_order": list(lockfile.install_order),
        "selection": (
            {
                "profile": lockfile.selection.profile,
                "interaction_mode": lockfile.selection.interaction_mode,
                "profile_source": lockfile.selection.profile_source,
                "interaction_mode_source": lockfile.selection.interaction_mode_source,
            }
            if lockfile.selection is not None
            else None
        ),
        "policy": (
            {
                "profile": lockfile.policy.profile,
                "source": lockfile.policy.source,
                "allowed_lifecycle_statuses": list(lockfile.policy.allowed_lifecycle_statuses),
                "allowed_trust_tiers": list(lockfile.policy.allowed_trust_tiers),
                "max_token_estimate": lockfile.policy.max_token_estimate,
                "max_content_size_bytes": lockfile.policy.max_content_size_bytes,
                "max_total_token_estimate": lockfile.policy.max_total_token_estimate,
                "max_total_content_size_bytes": lockfile.policy.max_total_content_size_bytes,
            }
            if lockfile.policy is not None
            else None
        ),
        "governance": [
            {
                "rule": item.rule,
                "passed": item.passed,
                "message": item.message,
                "node_id": item.node_id,
            }
            for item in lockfile.governance
        ],
    }


def _node_id(slug: str, version: str) -> str:
    return f"{slug}@{version}"


def _artifact_ref(slug: str, version: str) -> str:
    return f"/skills/{slug}/{version}/content"
