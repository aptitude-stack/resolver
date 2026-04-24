from __future__ import annotations

import json

from aptitude_resolver.domain.models import (
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
)
from aptitude_resolver.domain.policy import PolicyEvaluation
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.application.debug_artifacts import write_install_debug_artifacts


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
        published_at="2026-03-28T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )


def test_write_install_debug_artifacts_writes_expected_files_and_shapes(
    tmp_path,
) -> None:
    target = tmp_path / "skill_demo"
    graph = ResolutionGraph(
        root=SkillCoordinate(slug="python.lint", version="1.2.3"),
        nodes=[
            _node("python.base", "1.0.0"),
            _node("python.lint", "1.2.3"),
        ],
        edges=[
            DependencyEdge(
                source=SkillCoordinate(slug="python.lint", version="1.2.3"),
                target=SkillCoordinate(slug="python.base", version="1.0.0"),
            )
        ],
        install_order=[
            SkillCoordinate(slug="python.base", version="1.0.0"),
            SkillCoordinate(slug="python.lint", version="1.2.3"),
        ],
        conflicts=[],
    )

    write_install_debug_artifacts(
        target=target,
        graph=graph,
        trace=[
            TraceEntry(
                stage="execution",
                action="materialize_locked_skill",
                message="Materialized locked skill python.base@1.0.0.",
                data={"node_id": "python.base@1.0.0"},
            )
        ],
        policy_evaluations=[
            PolicyEvaluation(
                rule="allowed_lifecycle_status",
                passed=True,
                message="Lifecycle allowed.",
                coordinate=SkillCoordinate(slug="python.lint", version="1.2.3"),
            )
        ],
    )

    resolution_dir = target / "resolution"
    graph_payload = json.loads(
        (resolution_dir / "graph.json").read_text(encoding="utf-8")
    )
    trace_payload = json.loads(
        (resolution_dir / "trace.json").read_text(encoding="utf-8")
    )
    policy_payload = json.loads(
        (resolution_dir / "policy.json").read_text(encoding="utf-8")
    )

    assert sorted(path.name for path in resolution_dir.iterdir()) == [
        "graph.json",
        "policy.json",
        "trace.json",
    ]
    assert graph_payload["root"] == {"slug": "python.lint", "version": "1.2.3"}
    assert graph_payload["install_order"] == [
        {"slug": "python.base", "version": "1.0.0"},
        {"slug": "python.lint", "version": "1.2.3"},
    ]
    assert trace_payload == [
        {
            "stage": "execution",
            "action": "materialize_locked_skill",
            "message": "Materialized locked skill python.base@1.0.0.",
            "data": {"node_id": "python.base@1.0.0"},
        }
    ]
    assert policy_payload == [
        {
            "rule": "allowed_lifecycle_status",
            "passed": True,
            "message": "Lifecycle allowed.",
            "coordinate": {"slug": "python.lint", "version": "1.2.3"},
        }
    ]
