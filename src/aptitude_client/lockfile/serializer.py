"""Lockfile build and serialization helpers."""

from __future__ import annotations

import json

from aptitude_client.domain.models import ResolutionGraph
from aptitude_client.domain.policy import PolicyEvaluation
from aptitude_client.lockfile.model import (
    GovernanceSnapshotEntry,
    LockRoot,
    Lockfile,
    LockedEdge,
    LockedSkill,
)


def build_lockfile(
    *,
    graph: ResolutionGraph,
    requested_query: str,
    requested_version: str | None,
    selection_mode: str,
    policy_evaluations: list[PolicyEvaluation],
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
