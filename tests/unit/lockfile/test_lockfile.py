from __future__ import annotations

from dataclasses import replace
import json

import pytest

from aptitude_resolver.domain.errors import InvalidLockfileError
from aptitude_resolver.domain.models import (
    DependencySpec,
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillMetadata,
    SkillCoordinate,
    VersionSummary,
)
from aptitude_resolver.domain.policy import PolicyEvaluation, SelectionPreferences
from aptitude_resolver.lockfile import (
    build_lockfile,
    lockfile_to_dict,
    LockRoot,
    Lockfile,
    merge_lockfiles,
    parse_lockfile,
    replay_lockfile,
    serialize_lockfile,
)
from aptitude_resolver.resolution.graph import resolve_recursive_graph


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
        self.dependencies_by_coordinate: dict[
            tuple[str, str], list[DependencySpec]
        ] = {}

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        return self.metadata_by_coordinate[(slug, version)]

    def fetch_direct_dependencies(
        self, slug: str, version: str
    ) -> list[DependencySpec]:
        return list(self.dependencies_by_coordinate.get((slug, version), []))

    def list_skill_versions(self, slug: str) -> list[VersionSummary]:
        return [
            VersionSummary(
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
            for (candidate_slug, _), metadata in self.metadata_by_coordinate.items()
            if candidate_slug == slug
        ]


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


def _single_root_lock(slug: str, version: str) -> Lockfile:
    coordinate = SkillCoordinate(slug=slug, version=version)
    graph = ResolutionGraph(
        root=coordinate,
        nodes=[_node(slug, version, published_at="2026-03-18T00:00:00Z")],
        edges=[],
        install_order=[coordinate],
        conflicts=[],
    )
    return build_lockfile(
        graph=graph,
        requested_query=slug,
        requested_version=version,
        selection_mode="exact",
        policy_evaluations=[],
    )


def test_build_lockfile_serializes_and_parses_without_meaningful_loss() -> None:
    dependency = SkillCoordinate(slug="python-base", version="1.0.0")
    root = SkillCoordinate(slug="python-lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version, published_at="2026-03-18T00:00:00Z"),
            _node(
                dependency.slug, dependency.version, published_at="2026-03-17T00:00:00Z"
            ),
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
        selection_preferences=SelectionPreferences(
            profile="high-trust",
            interaction_mode="always",
            profile_source="workspace_config",
            interaction_mode_source="cli_override",
        ),
    )

    assert lockfile.generated_at == "2026-03-18T00:00:00Z"
    assert [node.node_id for node in lockfile.nodes] == [
        "python-base@1.0.0",
        "python-lint@1.2.3",
    ]
    assert lockfile.nodes[0].tags == ["a-tag", "z-tag"]
    assert lockfile.nodes[0].headers == {"entrypoint": "main", "runtime": "python"}
    assert lockfile.install_order == ["python-base@1.0.0", "python-lint@1.2.3"]
    assert lockfile.governance[0].node_id == "python-lint@1.2.3"
    assert lockfile.policy is not None
    assert lockfile.policy.profile == "default"
    assert lockfile.policy.source == "client_default"
    assert lockfile.policy.allowed_trust_tiers == ["verified", "internal", "untrusted"]
    assert lockfile.policy.max_token_estimate is None
    assert lockfile.policy.max_content_size_bytes is None
    assert lockfile.policy.max_total_token_estimate is None
    assert lockfile.policy.max_total_content_size_bytes is None
    assert lockfile.selection is not None
    assert lockfile.selection.profile == "high-trust"
    assert lockfile.selection.interaction_mode == "always"
    assert lockfile.selection.profile_source == "workspace_config"
    assert lockfile.selection.interaction_mode_source == "cli_override"

    parsed = parse_lockfile(serialize_lockfile(lockfile))

    assert parsed == lockfile


def test_replay_lockfile_uses_only_locked_nodes_edges_and_install_order() -> None:
    dependency = SkillCoordinate(slug="python-base", version="1.0.0")
    root = SkillCoordinate(slug="python-lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version, published_at="2026-03-18T00:00:00Z"),
            _node(
                dependency.slug, dependency.version, published_at="2026-03-17T00:00:00Z"
            ),
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

    assert replayed.root_node.node_id == "python-lint@1.2.3"
    assert [node.node_id for node in replayed.install_order] == [
        "python-base@1.0.0",
        "python-lint@1.2.3",
    ]
    assert [
        edge.target_node_id for edge in replayed.edges_by_source["python-lint@1.2.3"]
    ] == ["python-base@1.0.0"]


def test_replay_lockfile_rejects_missing_install_order_nodes() -> None:
    dependency = SkillCoordinate(slug="python-base", version="1.0.0")
    root = SkillCoordinate(slug="python-lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(root.slug, root.version, published_at="2026-03-18T00:00:00Z"),
            _node(
                dependency.slug, dependency.version, published_at="2026-03-17T00:00:00Z"
            ),
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


def test_merge_lockfiles_accumulates_roots_and_preserves_existing_pins() -> None:
    first = _single_root_lock("python-lint", "1.2.3")
    second = _single_root_lock("js-lint", "2.1.0")

    merged = merge_lockfiles(first, second)

    assert merged.version == 2
    assert merged.root.selected_node_id == "js-lint@2.1.0"
    assert [root.selected_node_id for root in merged.roots] == [
        "python-lint@1.2.3",
        "js-lint@2.1.0",
    ]
    assert [node.node_id for node in merged.nodes] == [
        "python-lint@1.2.3",
        "js-lint@2.1.0",
    ]
    assert merged.install_order == ["python-lint@1.2.3", "js-lint@2.1.0"]


def test_merge_lockfiles_is_idempotent_and_accepts_v1_locks() -> None:
    lockfile = _single_root_lock("python-lint", "1.2.3")
    payload = lockfile_to_dict(lockfile)
    payload["version"] = 1
    payload.pop("roots")
    v1_lockfile = parse_lockfile(json.dumps(payload))

    merged = merge_lockfiles(v1_lockfile, lockfile)

    assert [root.selected_node_id for root in merged.roots] == ["python-lint@1.2.3"]
    assert [node.node_id for node in merged.nodes] == ["python-lint@1.2.3"]


def test_replay_lockfile_rejects_missing_cumulative_root() -> None:
    lockfile = _single_root_lock("python-lint", "1.2.3")
    corrupted = replace(
        lockfile,
        roots=[
            LockRoot(
                request="missing",
                requested_version=None,
                selected_node_id="missing@1.0.0",
                selection_mode="exact",
            )
        ],
    )

    with pytest.raises(InvalidLockfileError, match="missing@1.0.0"):
        replay_lockfile(corrupted)


def test_lockfile_bytes_are_identical_across_reordered_registry_dependency_inputs() -> (
    None
):
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
