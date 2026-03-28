from __future__ import annotations

import pytest

from aptitude_client.domain.errors import InvalidLockfileError
from aptitude_client.domain.models import (
    DependencySpec,
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillMetadata,
    SkillCoordinate,
)
from aptitude_client.domain.policy import PolicyEvaluation
from aptitude_client.lockfile import build_lockfile, parse_lockfile, replay_lockfile, serialize_lockfile
from aptitude_client.resolver.graph import resolve_recursive_graph


def _node(slug: str, version: str, *, published_at: str) -> ResolvedSkillNode:
    return ResolvedSkillNode(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=slug,
        description=f"{slug} description",
        tags=["z-tag", "a-tag"],
        headers={"runtime": "python", "entrypoint": "main"},
        rendered_summary=f"{slug} summary",
        lifecycle_status="published",
        trust_tier="internal",
        published_at=published_at,
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )


class FakeRegistryClient:
    def __init__(self) -> None:
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.dependencies_by_coordinate: dict[tuple[str, str], list[DependencySpec]] = {}

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        return self.metadata_by_coordinate[(slug, version)]

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]:
        return list(self.dependencies_by_coordinate.get((slug, version), []))


def _metadata(slug: str, version: str, *, published_at: str) -> SkillMetadata:
    return SkillMetadata(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=slug,
        description=f"{slug} description",
        tags=["z-tag", "a-tag"],
        headers={"runtime": "python", "entrypoint": "main"},
        inputs_schema={"type": "object"},
        outputs_schema={"type": "object"},
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
        rendered_summary=f"{slug} summary",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        lifecycle_status="published",
        trust_tier="internal",
        published_at=published_at,
    )


def test_build_lockfile_serializes_and_parses_without_meaningful_loss() -> None:
    dependency = SkillCoordinate(slug="python.base", version="1.0.0")
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version, published_at="2026-03-18T00:00:00Z"),
            _node(dependency.slug, dependency.version, published_at="2026-03-17T00:00:00Z"),
        ],
        edges=[DependencyEdge(source=root, target=dependency, markers=["linux"])],
        install_order=[dependency, root],
        conflicts=[],
    )

    lockfile = build_lockfile(
        graph=graph,
        requested_query="python lint",
        requested_version=None,
        selection_mode="single_candidate",
        policy_evaluations=[
            PolicyEvaluation(
                rule="allowed_lifecycle_status",
                passed=True,
                message="Lifecycle allowed.",
                coordinate=root,
            )
        ],
    )

    assert lockfile.generated_at == "2026-03-18T00:00:00Z"
    assert [node.node_id for node in lockfile.nodes] == [
        "python.base@1.0.0",
        "python.lint@1.2.3",
    ]
    assert lockfile.nodes[0].tags == ["a-tag", "z-tag"]
    assert lockfile.nodes[0].headers == {"entrypoint": "main", "runtime": "python"}
    assert lockfile.install_order == ["python.base@1.0.0", "python.lint@1.2.3"]
    assert lockfile.governance[0].node_id == "python.lint@1.2.3"

    parsed = parse_lockfile(serialize_lockfile(lockfile))

    assert parsed == lockfile


def test_replay_lockfile_uses_only_locked_nodes_edges_and_install_order() -> None:
    dependency = SkillCoordinate(slug="python.base", version="1.0.0")
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version, published_at="2026-03-18T00:00:00Z"),
            _node(dependency.slug, dependency.version, published_at="2026-03-17T00:00:00Z"),
        ],
        edges=[DependencyEdge(source=root, target=dependency)],
        install_order=[dependency, root],
        conflicts=[],
    )
    lockfile = build_lockfile(
        graph=graph,
        requested_query="python lint",
        requested_version=None,
        selection_mode="single_candidate",
        policy_evaluations=[],
    )

    replayed = replay_lockfile(lockfile)

    assert replayed.root_node.node_id == "python.lint@1.2.3"
    assert [node.node_id for node in replayed.install_order] == [
        "python.base@1.0.0",
        "python.lint@1.2.3",
    ]
    assert [
        edge.target_node_id for edge in replayed.edges_by_source["python.lint@1.2.3"]
    ] == ["python.base@1.0.0"]


def test_replay_lockfile_rejects_missing_install_order_nodes() -> None:
    dependency = SkillCoordinate(slug="python.base", version="1.0.0")
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version, published_at="2026-03-18T00:00:00Z"),
            _node(dependency.slug, dependency.version, published_at="2026-03-17T00:00:00Z"),
        ],
        edges=[DependencyEdge(source=root, target=dependency)],
        install_order=[root],
        conflicts=[],
    )
    lockfile = build_lockfile(
        graph=graph,
        requested_query="python lint",
        requested_version=None,
        selection_mode="single_candidate",
        policy_evaluations=[],
    )

    with pytest.raises(InvalidLockfileError):
        replay_lockfile(lockfile)


def test_lockfile_bytes_are_identical_across_reordered_registry_dependency_inputs() -> None:
    first_registry = FakeRegistryClient()
    second_registry = FakeRegistryClient()
    root = SkillCoordinate(slug="root.skill", version="1.0.0")

    for registry_client in (first_registry, second_registry):
        registry_client.metadata_by_coordinate[("root.skill", "1.0.0")] = _metadata(
            "root.skill",
            "1.0.0",
            published_at="2026-03-18T00:00:00Z",
        )
        registry_client.metadata_by_coordinate[("a.dep", "1.0.0")] = _metadata(
            "a.dep",
            "1.0.0",
            published_at="2026-03-17T00:00:00Z",
        )
        registry_client.metadata_by_coordinate[("b.dep", "1.0.0")] = _metadata(
            "b.dep",
            "1.0.0",
            published_at="2026-03-16T00:00:00Z",
        )
        registry_client.dependencies_by_coordinate[("a.dep", "1.0.0")] = []
        registry_client.dependencies_by_coordinate[("b.dep", "1.0.0")] = []

    first_registry.dependencies_by_coordinate[("root.skill", "1.0.0")] = [
        DependencySpec(slug="b.dep", version="1.0.0"),
        DependencySpec(slug="a.dep", version="1.0.0"),
    ]
    second_registry.dependencies_by_coordinate[("root.skill", "1.0.0")] = [
        DependencySpec(slug="a.dep", version="1.0.0"),
        DependencySpec(slug="b.dep", version="1.0.0"),
    ]

    first_graph, _ = resolve_recursive_graph(root, first_registry)
    second_graph, _ = resolve_recursive_graph(root, second_registry)

    first_lock = serialize_lockfile(
        build_lockfile(
            graph=first_graph,
            requested_query="root skill",
            requested_version=None,
            selection_mode="single_candidate",
            policy_evaluations=[],
        )
    )
    second_lock = serialize_lockfile(
        build_lockfile(
            graph=second_graph,
            requested_query="root skill",
            requested_version=None,
            selection_mode="single_candidate",
            policy_evaluations=[],
        )
    )

    assert [(item.slug, item.version) for item in first_graph.install_order] == [
        (item.slug, item.version) for item in second_graph.install_order
    ]
    assert first_lock == second_lock
