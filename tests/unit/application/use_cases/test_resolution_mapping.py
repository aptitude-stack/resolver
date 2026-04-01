from __future__ import annotations

from aptitude.application.queries import ResolutionArtifact
from aptitude.application.use_cases.resolution_mapping import (
    candidate_to_dto,
    execution_plan_to_dto,
    graph_to_dto,
    lockfile_to_dto,
    policy_to_dto,
    selected_skill_to_dto,
    trace_to_dto,
)
from aptitude.domain.models import (
    ConflictRecord,
    DependencyEdge,
    DiscoveryCandidate,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
    VersionSummary,
)
from aptitude.domain.policy import PolicyEvaluation
from aptitude.domain.tracing import TraceEntry
from aptitude.execution.plan import ExecutionPlan, ExecutionStep
from aptitude.lockfile.model import (
    GovernanceSnapshotEntry,
    LockedEdge,
    LockedSkill,
    LockRoot,
    Lockfile,
    PolicySnapshot,
    SelectionSnapshot,
)


def _version_summary(
    slug: str,
    version: str,
    *,
    name: str,
    runtime: str = "python",
) -> VersionSummary:
    return VersionSummary(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=f"{name} description",
        tags=["lint", "python"],
        headers={"runtime": runtime, "entrypoint": "main"},
        rendered_summary=f"{name} summary",
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        token_estimate=120,
        maturity_score=0.9,
        security_score=0.95,
    )


def _resolved_node(slug: str, version: str, *, name: str) -> ResolvedSkillNode:
    version_summary = _version_summary(slug, version, name=name)
    return ResolvedSkillNode(
        coordinate=version_summary.coordinate,
        name=version_summary.name,
        description=version_summary.description,
        tags=list(version_summary.tags),
        headers=dict(version_summary.headers),
        rendered_summary=version_summary.rendered_summary,
        lifecycle_status=version_summary.lifecycle_status,
        trust_tier=version_summary.trust_tier,
        published_at=version_summary.published_at,
        content_checksum_algorithm=version_summary.content_checksum_algorithm or "",
        content_checksum_digest=version_summary.content_checksum_digest or "",
        content_size_bytes=version_summary.content_size_bytes,
        token_estimate=version_summary.token_estimate,
        maturity_score=version_summary.maturity_score,
        security_score=version_summary.security_score,
    )


def _locked_skill(slug: str, version: str, *, name: str) -> LockedSkill:
    return LockedSkill(
        node_id=f"{slug}@{version}",
        slug=slug,
        version=version,
        artifact_ref=f"/skills/{slug}/{version}/content",
        name=name,
        description=f"{name} description",
        tags=["lint", "python"],
        headers={"runtime": "python", "entrypoint": "main"},
        rendered_summary=f"{name} summary",
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
    )


def test_lockfile_to_dto_preserves_nested_content_and_optional_snapshots() -> None:
    lockfile = Lockfile(
        version=1,
        generated_at="2026-03-18T00:00:00Z",
        client_version="0.1.0",
        root=LockRoot(
            request="python lint",
            requested_version=None,
            selected_node_id="python.lint@1.2.3",
            selection_mode="single_candidate",
        ),
        nodes=[_locked_skill("python.lint", "1.2.3", name="Python Lint")],
        edges=[
            LockedEdge(
                source_node_id="python.lint@1.2.3",
                target_node_id="dep.core@0.9.0",
                markers=["linux"],
            )
        ],
        install_order=["dep.core@0.9.0", "python.lint@1.2.3"],
        selection=SelectionSnapshot(
            profile="high-trust",
            interaction_mode="always",
            profile_source="workspace_config",
            interaction_mode_source="cli_override",
        ),
        policy=PolicySnapshot(
            profile="default",
            source="client_default",
            allowed_lifecycle_statuses=["published"],
            allowed_trust_tiers=["verified", "internal"],
            max_token_estimate=300,
            max_content_size_bytes=2048,
            max_total_token_estimate=600,
            max_total_content_size_bytes=4096,
        ),
        governance=[
            GovernanceSnapshotEntry(
                rule="allowed_trust_tiers",
                passed=True,
                message="Trust allowed.",
                node_id="python.lint@1.2.3",
            )
        ],
    )

    dto = lockfile_to_dto(lockfile)

    assert dto.root.selected_node_id == "python.lint@1.2.3"
    assert dto.nodes[0].headers == {"runtime": "python", "entrypoint": "main"}
    assert dto.nodes[0].content_checksum == {
        "algorithm": "sha256",
        "digest": "digest-python.lint-1.2.3",
        "size_bytes": 256,
    }
    assert dto.selection is not None
    assert dto.selection.interaction_mode == "always"
    assert dto.policy is not None
    assert dto.policy.max_total_token_estimate == 600
    assert dto.governance[0].node_id == "python.lint@1.2.3"


def test_lockfile_to_dto_omits_optional_snapshots_when_absent() -> None:
    lockfile = Lockfile(
        version=1,
        generated_at=None,
        client_version=None,
        root=LockRoot(
            request="python lint",
            requested_version=None,
            selected_node_id="python.lint@1.2.3",
            selection_mode="single_candidate",
        ),
        nodes=[_locked_skill("python.lint", "1.2.3", name="Python Lint")],
        edges=[],
        install_order=["python.lint@1.2.3"],
        selection=None,
        policy=None,
        governance=[],
    )

    dto = lockfile_to_dto(lockfile)

    assert dto.selection is None
    assert dto.policy is None


def test_resolution_mapping_helpers_preserve_runtime_trace_and_root_selection() -> None:
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    dependency = SkillCoordinate(slug="dep.core", version="0.9.0")
    candidate = DiscoveryCandidate(
        slug="python.lint",
        selected_version=_version_summary("python.lint", "1.2.3", name="Python Lint"),
        labels=["python", "lint"],
        matched_labels=["python"],
        match_reasons=["exact_name_match"],
        ranking_position=1,
        selection_details=["tokens=120", "size=256B"],
        selection_reason="Closer exact name match than dep.core.",
    )
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _resolved_node("dep.core", "0.9.0", name="Dependency Core"),
            _resolved_node("python.lint", "1.2.3", name="Python Lint"),
        ],
        edges=[DependencyEdge(source=root, target=dependency, markers=["linux"])],
        install_order=[dependency, root],
        conflicts=[
            ConflictRecord(
                code="sample_conflict",
                message="Conflict summary.",
                coordinates=[root, dependency],
            )
        ],
    )
    lockfile = Lockfile(
        version=1,
        generated_at="2026-03-18T00:00:00Z",
        client_version="0.1.0",
        root=LockRoot(
            request="python lint",
            requested_version=None,
            selected_node_id="python.lint@1.2.3",
            selection_mode="single_candidate",
        ),
        nodes=[
            _locked_skill("dep.core", "0.9.0", name="Dependency Core"),
            _locked_skill("python.lint", "1.2.3", name="Python Lint"),
        ],
        edges=[
            LockedEdge(
                source_node_id="python.lint@1.2.3", target_node_id="dep.core@0.9.0"
            )
        ],
        install_order=["dep.core@0.9.0", "python.lint@1.2.3"],
        governance=[],
    )
    execution_plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                node_id="dep.core@0.9.0",
                skill="dep.core",
                version="0.9.0",
                artifact_ref="/skills/dep.core/0.9.0/content",
                action="materialize_local_skill",
            )
        ]
    )
    trace_entry = TraceEntry(
        stage="selection",
        action="explain_final_selection",
        message="Explained the winning candidate.",
        data={"decisive_signals": ["exact_name_match"]},
    )
    evaluation = PolicyEvaluation(
        rule="allowed_lifecycle_status",
        passed=True,
        message="Lifecycle allowed.",
        coordinate=root,
    )
    artifact = ResolutionArtifact(
        requested_query="python lint",
        requested_version=None,
        selection_mode="single_candidate",
        candidates=[candidate],
        selected_candidate=candidate,
        graph=graph,
        lockfile=lockfile,
        execution_plan=execution_plan,
        trace=[trace_entry],
        policy_evaluations=[evaluation],
    )

    candidate_dto = candidate_to_dto(candidate)
    graph_dto = graph_to_dto(graph)
    execution_plan_dto = execution_plan_to_dto(execution_plan)
    trace_dto = trace_to_dto(trace_entry)
    policy_dto = policy_to_dto(evaluation)
    summary_dto = selected_skill_to_dto(artifact)

    assert candidate_dto.runtime == "python"
    assert candidate_dto.token_estimate == 120
    assert candidate_dto.selection_reason == "Closer exact name match than dep.core."
    assert graph_dto.root.slug == "python.lint"
    assert graph_dto.edges[0].markers == ["linux"]
    assert graph_dto.conflicts[0].coordinates[1].slug == "dep.core"
    assert execution_plan_dto.steps[0].action == "materialize_local_skill"
    assert trace_dto.data == {"decisive_signals": ["exact_name_match"]}
    assert policy_dto.coordinate is not None
    assert policy_dto.coordinate.slug == "python.lint"
    assert summary_dto.name == "Python Lint"
    assert summary_dto.runtime == "python"
