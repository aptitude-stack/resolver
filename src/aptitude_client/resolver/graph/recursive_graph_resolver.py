"""Recursive dependency graph resolution."""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from aptitude_client.domain.errors import DependencyCycleError
from aptitude_client.domain.models import (
    DependencyEdge,
    DependencySpec,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
    SkillMetadata,
)
from aptitude_client.domain.tracing import TraceEntry
from aptitude_client.resolver.conflict import ensure_no_version_conflict
from aptitude_client.resolver.normalizer import normalize_dependency_selector


class RegistryResolvePort(Protocol):
    """Registry reads required for recursive graph resolution."""

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata: ...

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]: ...


def resolve_recursive_graph(
    root: SkillCoordinate,
    registry_client: RegistryResolvePort,
) -> tuple[ResolutionGraph, list[TraceEntry]]:
    """Resolve one selected root into a deterministic recursive graph."""

    nodes_by_key: dict[tuple[str, str], ResolvedSkillNode] = {}
    edges: list[DependencyEdge] = []
    selected_versions: dict[str, SkillCoordinate] = {}
    dependency_order: dict[tuple[str, str], list[SkillCoordinate]] = defaultdict(list)
    trace: list[TraceEntry] = []
    active_stack: list[SkillCoordinate] = []

    def visit(coordinate: SkillCoordinate) -> None:
        key = (coordinate.slug, coordinate.version)
        if coordinate in active_stack:
            cycle = [f"{item.slug}@{item.version}" for item in active_stack] + [
                f"{coordinate.slug}@{coordinate.version}"
            ]
            raise DependencyCycleError(cycle)

        if key in nodes_by_key:
            return

        ensure_no_version_conflict(selected_versions, coordinate)
        active_stack.append(coordinate)

        metadata = registry_client.fetch_skill_metadata(coordinate.slug, coordinate.version)
        dependencies = registry_client.fetch_direct_dependencies(coordinate.slug, coordinate.version)
        trace.append(
            TraceEntry(
                stage="resolver",
                action="list_dependencies_received",
                message=(
                    f"Received {len(dependencies)} direct dependencies for "
                    f"{coordinate.slug}@{coordinate.version}."
                ),
                data={
                    "source_slug": coordinate.slug,
                    "source_version": coordinate.version,
                    "dependencies": [_dependency_trace_label(item) for item in dependencies],
                },
            )
        )
        dependencies = sorted(dependencies, key=_dependency_sort_key)
        trace.append(
            TraceEntry(
                stage="resolver",
                action="list_dependencies_sorted",
                message=(
                    f"Canonicalized dependency order for "
                    f"{coordinate.slug}@{coordinate.version}."
                ),
                data={
                    "source_slug": coordinate.slug,
                    "source_version": coordinate.version,
                    "dependencies": [_dependency_trace_label(item) for item in dependencies],
                },
            )
        )
        trace.append(
            TraceEntry(
                stage="resolver",
                action="visit_node",
                message=f"Resolved exact node {coordinate.slug}@{coordinate.version}.",
                data={"dependency_count": len(dependencies)},
            )
        )

        nodes_by_key[key] = ResolvedSkillNode(
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
        selected_versions[coordinate.slug] = coordinate

        for index, dependency in enumerate(dependencies, start=1):
            target = normalize_dependency_selector(coordinate, dependency)
            trace.append(
                TraceEntry(
                    stage="resolver",
                    action="normalize_dependency_selector",
                    message=(
                        f"Normalized dependency {dependency.slug} from "
                        f"{coordinate.slug}@{coordinate.version} to "
                        f"{target.slug}@{target.version}."
                    ),
                    data={
                        "source_slug": coordinate.slug,
                        "source_version": coordinate.version,
                        "dependency_slug": dependency.slug,
                        "requested_version": dependency.version,
                        "requested_version_constraint": dependency.version_constraint,
                        "resolved_slug": target.slug,
                        "resolved_version": target.version,
                        "optional": dependency.optional,
                        "markers": list(dependency.markers),
                    },
                )
            )
            trace.append(
                TraceEntry(
                    stage="resolver",
                    action="traverse_dependency",
                    message=(
                        f"Traversing dependency {target.slug}@{target.version} from "
                        f"{coordinate.slug}@{coordinate.version}."
                    ),
                    data={
                        "source_slug": coordinate.slug,
                        "source_version": coordinate.version,
                        "target_slug": target.slug,
                        "target_version": target.version,
                        "traversal_position": index,
                    },
                )
            )
            dependency_order[key].append(target)
            edges.append(
                DependencyEdge(
                    source=coordinate,
                    target=target,
                    optional=dependency.optional,
                    markers=list(dependency.markers),
                )
            )
            visit(target)

        active_stack.pop()

    visit(root)

    install_order: list[SkillCoordinate] = []
    seen_install: set[tuple[str, str]] = set()

    def post_order(coordinate: SkillCoordinate) -> None:
        key = (coordinate.slug, coordinate.version)
        for dependency in dependency_order.get(key, []):
            dep_key = (dependency.slug, dependency.version)
            if dep_key not in seen_install:
                post_order(dependency)
        if key not in seen_install:
            seen_install.add(key)
            install_order.append(coordinate)

    post_order(root)

    graph = ResolutionGraph(
        root=root,
        nodes=sorted(
            nodes_by_key.values(),
            key=lambda node: (node.coordinate.slug, node.coordinate.version),
        ),
        edges=sorted(
            edges,
            key=lambda edge: (
                edge.source.slug,
                edge.source.version,
                edge.target.slug,
                edge.target.version,
                edge.edge_type,
                edge.optional,
                tuple(edge.markers),
            ),
        ),
        install_order=install_order,
    )
    return graph, trace


def _dependency_sort_key(dependency: DependencySpec) -> tuple[str, str, bool, tuple[str, ...]]:
    selector = (
        f"version:{dependency.version}"
        if dependency.version is not None
        else f"constraint:{dependency.version_constraint or ''}"
    )
    return (
        dependency.slug,
        selector,
        dependency.optional,
        tuple(sorted(dependency.markers)),
    )


def _dependency_trace_label(dependency: DependencySpec) -> str:
    selector = (
        dependency.version
        if dependency.version is not None
        else dependency.version_constraint or "<unspecified>"
    )
    suffix = "?" if dependency.optional else ""
    markers = f" [{','.join(sorted(dependency.markers))}]" if dependency.markers else ""
    return f"{dependency.slug}@{selector}{suffix}{markers}"
