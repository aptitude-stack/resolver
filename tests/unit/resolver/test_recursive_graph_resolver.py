from __future__ import annotations

import pytest

from aptitude_client.domain.errors import (
    DependencyCycleError,
    SkillNotFoundError,
    VersionConflictError,
)
from aptitude_client.domain.models import DependencySpec, SkillCoordinate, SkillMetadata
from aptitude_client.resolver.graph import resolve_recursive_graph


class FakeRegistryClient:
    def __init__(self) -> None:
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.dependencies_by_coordinate: dict[
            tuple[str, str], list[DependencySpec]
        ] = {}

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        try:
            return self.metadata_by_coordinate[(slug, version)]
        except KeyError as exc:
            raise SkillNotFoundError(
                f"Skill version not found: {slug}@{version}"
            ) from exc

    def fetch_direct_dependencies(
        self, slug: str, version: str
    ) -> list[DependencySpec]:
        return list(self.dependencies_by_coordinate.get((slug, version), []))


def _metadata(slug: str, version: str, *, name: str) -> SkillMetadata:
    return SkillMetadata(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=f"{name} description",
        tags=[slug.split(".")[-1]],
        headers={"runtime": "python"},
        inputs_schema={"type": "object"},
        outputs_schema={"type": "object"},
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
        rendered_summary=f"{name} summary",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
    )


def test_recursive_graph_resolver_builds_full_graph_and_install_order() -> None:
    registry_client = FakeRegistryClient()
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
    )
    registry_client.metadata_by_coordinate[("python.base", "1.0.0")] = _metadata(
        "python.base",
        "1.0.0",
        name="Python Base",
    )
    registry_client.metadata_by_coordinate[("python.fs", "2.0.0")] = _metadata(
        "python.fs",
        "2.0.0",
        name="Python FS",
    )
    registry_client.dependencies_by_coordinate[("python.lint", "1.2.3")] = [
        DependencySpec(slug="python.base", version="1.0.0"),
        DependencySpec(slug="python.fs", version="2.0.0"),
    ]

    graph, trace = resolve_recursive_graph(
        SkillCoordinate(slug="python.lint", version="1.2.3"),
        registry_client,
    )

    assert graph.root == SkillCoordinate(slug="python.lint", version="1.2.3")
    assert [node.coordinate.slug for node in graph.nodes] == [
        "python.base",
        "python.fs",
        "python.lint",
    ]
    assert [(edge.source.slug, edge.target.slug) for edge in graph.edges] == [
        ("python.lint", "python.base"),
        ("python.lint", "python.fs"),
    ]
    assert [item.slug for item in graph.install_order] == [
        "python.base",
        "python.fs",
        "python.lint",
    ]
    assert any(item.action == "visit_node" for item in trace)
    received_trace = next(
        item for item in trace if item.action == "list_dependencies_received"
    )
    sorted_trace = next(
        item for item in trace if item.action == "list_dependencies_sorted"
    )
    traversal_traces = [item for item in trace if item.action == "traverse_dependency"]
    assert received_trace.data["dependencies"] == [
        "python.base@1.0.0",
        "python.fs@2.0.0",
    ]
    assert sorted_trace.data["dependencies"] == ["python.base@1.0.0", "python.fs@2.0.0"]
    assert [item.data["target_slug"] for item in traversal_traces] == [
        "python.base",
        "python.fs",
    ]
    normalization_traces = [
        item for item in trace if item.action == "normalize_dependency_selector"
    ]
    assert len(normalization_traces) == 2
    assert normalization_traces[0].data == {
        "source_slug": "python.lint",
        "source_version": "1.2.3",
        "dependency_slug": "python.base",
        "requested_version": "1.0.0",
        "requested_version_constraint": None,
        "resolved_slug": "python.base",
        "resolved_version": "1.0.0",
        "optional": False,
        "markers": [],
    }


def test_recursive_graph_resolver_detects_cycles() -> None:
    registry_client = FakeRegistryClient()
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
    )
    registry_client.metadata_by_coordinate[("python.base", "1.0.0")] = _metadata(
        "python.base",
        "1.0.0",
        name="Python Base",
    )
    registry_client.dependencies_by_coordinate[("python.lint", "1.2.3")] = [
        DependencySpec(slug="python.base", version="1.0.0")
    ]
    registry_client.dependencies_by_coordinate[("python.base", "1.0.0")] = [
        DependencySpec(slug="python.lint", version="1.2.3")
    ]

    with pytest.raises(DependencyCycleError):
        resolve_recursive_graph(
            SkillCoordinate(slug="python.lint", version="1.2.3"),
            registry_client,
        )


def test_recursive_graph_resolver_detects_version_conflicts() -> None:
    registry_client = FakeRegistryClient()
    registry_client.metadata_by_coordinate[("root.skill", "1.0.0")] = _metadata(
        "root.skill",
        "1.0.0",
        name="Root Skill",
    )
    registry_client.metadata_by_coordinate[("a.skill", "1.0.0")] = _metadata(
        "a.skill",
        "1.0.0",
        name="A Skill",
    )
    registry_client.metadata_by_coordinate[("shared.dep", "1.0.0")] = _metadata(
        "shared.dep",
        "1.0.0",
        name="Shared Dep",
    )
    registry_client.metadata_by_coordinate[("shared.dep", "2.0.0")] = _metadata(
        "shared.dep",
        "2.0.0",
        name="Shared Dep",
    )
    registry_client.dependencies_by_coordinate[("root.skill", "1.0.0")] = [
        DependencySpec(slug="a.skill", version="1.0.0"),
        DependencySpec(slug="shared.dep", version="1.0.0"),
    ]
    registry_client.dependencies_by_coordinate[("a.skill", "1.0.0")] = [
        DependencySpec(slug="shared.dep", version="2.0.0")
    ]

    with pytest.raises(VersionConflictError):
        resolve_recursive_graph(
            SkillCoordinate(slug="root.skill", version="1.0.0"),
            registry_client,
        )


def test_recursive_graph_resolver_is_order_independent_for_reordered_dependencies() -> (
    None
):
    first_registry = FakeRegistryClient()
    second_registry = FakeRegistryClient()
    root = SkillCoordinate(slug="root.skill", version="1.0.0")

    for registry_client in (first_registry, second_registry):
        registry_client.metadata_by_coordinate[("root.skill", "1.0.0")] = _metadata(
            "root.skill",
            "1.0.0",
            name="Root Skill",
        )
        registry_client.metadata_by_coordinate[("a.dep", "1.0.0")] = _metadata(
            "a.dep",
            "1.0.0",
            name="A Dep",
        )
        registry_client.metadata_by_coordinate[("b.dep", "1.0.0")] = _metadata(
            "b.dep",
            "1.0.0",
            name="B Dep",
        )
        registry_client.metadata_by_coordinate[("leaf.dep", "1.0.0")] = _metadata(
            "leaf.dep",
            "1.0.0",
            name="Leaf Dep",
        )
        registry_client.dependencies_by_coordinate[("a.dep", "1.0.0")] = [
            DependencySpec(slug="leaf.dep", version="1.0.0")
        ]
        registry_client.dependencies_by_coordinate[("b.dep", "1.0.0")] = []
        registry_client.dependencies_by_coordinate[("leaf.dep", "1.0.0")] = []

    first_registry.dependencies_by_coordinate[("root.skill", "1.0.0")] = [
        DependencySpec(slug="b.dep", version="1.0.0"),
        DependencySpec(slug="a.dep", version="1.0.0"),
    ]
    second_registry.dependencies_by_coordinate[("root.skill", "1.0.0")] = [
        DependencySpec(slug="a.dep", version="1.0.0"),
        DependencySpec(slug="b.dep", version="1.0.0"),
    ]

    first_graph, first_trace = resolve_recursive_graph(root, first_registry)
    second_graph, second_trace = resolve_recursive_graph(root, second_registry)

    assert [
        (node.coordinate.slug, node.coordinate.version) for node in first_graph.nodes
    ] == [
        (node.coordinate.slug, node.coordinate.version) for node in second_graph.nodes
    ]
    assert [(edge.source.slug, edge.target.slug) for edge in first_graph.edges] == [
        (edge.source.slug, edge.target.slug) for edge in second_graph.edges
    ]
    assert [(item.slug, item.version) for item in first_graph.install_order] == [
        (item.slug, item.version) for item in second_graph.install_order
    ]
    assert [
        item.data["dependencies"]
        for item in first_trace
        if item.action == "list_dependencies_sorted"
    ] == [
        item.data["dependencies"]
        for item in second_trace
        if item.action == "list_dependencies_sorted"
    ]
    assert [
        item.data["target_slug"]
        for item in first_trace
        if item.action == "traverse_dependency"
    ] == [
        item.data["target_slug"]
        for item in second_trace
        if item.action == "traverse_dependency"
    ]
