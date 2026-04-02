from __future__ import annotations

import pytest

from aptitude_resolver.domain.models import (
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
)
from aptitude_resolver.resolution.validation import validate_resolution_graph


def _node(slug: str, version: str) -> ResolvedSkillNode:
    return ResolvedSkillNode(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=slug,
        description=f"{slug} description",
        tags=["lint"],
        headers={"runtime": "python"},
        rendered_summary=f"{slug} summary",
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )


def test_validate_resolution_graph_accepts_edges_referencing_known_nodes() -> None:
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    dependency = SkillCoordinate(slug="dep.core", version="0.9.0")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version),
            _node(dependency.slug, dependency.version),
        ],
        edges=[DependencyEdge(source=root, target=dependency)],
        install_order=[dependency, root],
    )

    validate_resolution_graph(graph)


def test_validate_resolution_graph_rejects_missing_edge_source() -> None:
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    dependency = SkillCoordinate(slug="dep.core", version="0.9.0")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version),
            _node(dependency.slug, dependency.version),
        ],
        edges=[
            DependencyEdge(
                source=SkillCoordinate(slug="missing.dep", version="9.9.9"),
                target=dependency,
            )
        ],
        install_order=[dependency, root],
    )

    with pytest.raises(
        ValueError, match="Resolution graph edge source was not present in nodes."
    ):
        validate_resolution_graph(graph)


def test_validate_resolution_graph_rejects_missing_edge_target() -> None:
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    dependency = SkillCoordinate(slug="dep.core", version="0.9.0")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version),
            _node(dependency.slug, dependency.version),
        ],
        edges=[
            DependencyEdge(
                source=root,
                target=SkillCoordinate(slug="missing.dep", version="9.9.9"),
            )
        ],
        install_order=[dependency, root],
    )

    with pytest.raises(
        ValueError, match="Resolution graph edge target was not present in nodes."
    ):
        validate_resolution_graph(graph)
