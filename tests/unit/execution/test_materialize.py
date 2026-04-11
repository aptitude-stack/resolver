from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest
import aptitude_resolver.execution.materialize as materialize_module

from aptitude_resolver.domain.errors import ContentChecksumMismatchError
from aptitude_resolver.domain.models import (
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
)
from aptitude_resolver.domain.policy import PolicyEvaluation
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.execution import (
    build_execution_plan,
    materialize_lockfile,
    write_install_debug_artifacts,
)
from aptitude_resolver.lockfile import SelectionSnapshot, build_lockfile, load_lockfile


class FakeRegistryClient:
    def __init__(self, content_by_coordinate: dict[tuple[str, str], str]) -> None:
        self.content_by_coordinate = content_by_coordinate
        self.calls: list[tuple[str, str]] = []

    def fetch_skill_content(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> str:
        self.calls.append((slug, version))
        return self.content_by_coordinate[(slug, version)]


def _node(slug: str, version: str, content: str) -> ResolvedSkillNode:
    return ResolvedSkillNode(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=slug,
        description=f"{slug} description",
        tags=[slug.split(".")[-1]],
        headers={"runtime": "python"},
        rendered_summary=f"{slug} summary",
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        content_size_bytes=len(content.encode("utf-8")),
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )


def _lockfile(content_by_coordinate: dict[tuple[str, str], str]):
    dependency = SkillCoordinate(slug="python.base", version="1.0.0")
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(
                dependency.slug,
                dependency.version,
                content_by_coordinate[(dependency.slug, dependency.version)],
            ),
            _node(
                root.slug,
                root.version,
                content_by_coordinate[(root.slug, root.version)],
            ),
        ],
        edges=[DependencyEdge(source=root, target=dependency)],
        install_order=[dependency, root],
        conflicts=[],
    )
    return build_lockfile(
        graph=graph,
        requested_query="python lint",
        requested_version=None,
        selection_mode="single_candidate",
        policy_evaluations=[],
    )


def test_build_execution_plan_uses_locked_install_order() -> None:
    lockfile = _lockfile(
        {
            ("python.base", "1.0.0"): "# Python Base\n",
            ("python.lint", "1.2.3"): "# Python Lint\n",
        }
    )

    execution_plan = build_execution_plan(lockfile)

    assert [step.node_id for step in execution_plan.steps] == [
        "python.base@1.0.0",
        "python.lint@1.2.3",
    ]


def test_materialize_lockfile_writes_skills_and_resolution_artifacts(tmp_path) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): "# Python Base\n",
        ("python.lint", "1.2.3"): "# Python Lint\n",
    }
    registry_client = FakeRegistryClient(content_by_coordinate)
    lockfile = _lockfile(content_by_coordinate)

    result = materialize_lockfile(
        target=tmp_path / "skill_demo",
        lockfile=lockfile,
        registry_client=registry_client,
    )

    materialized_root = tmp_path / "skill_demo"
    assert materialized_root.exists()
    assert registry_client.calls == [("python.base", "1.0.0"), ("python.lint", "1.2.3")]
    assert (
        materialized_root / "skills" / "python.lint" / "1.2.3" / "content.md"
    ).read_text(encoding="utf-8") == "# Python Lint\n"
    loaded_lockfile = load_lockfile(
        materialized_root / "resolution" / "aptitude.lock.json"
    )
    assert loaded_lockfile == lockfile
    assert [item.action for item in result.trace] == [
        "materialize_locked_skill",
        "materialize_locked_skill",
    ]


def test_materialize_lockfile_raises_when_checksum_does_not_match(tmp_path) -> None:
    lockfile = _lockfile(
        {
            ("python.lint", "1.2.3"): "# Python Lint\n",
            ("python.base", "1.0.0"): "# Python Base\n",
        }
    )
    registry_client = FakeRegistryClient(
        {
            ("python.base", "1.0.0"): "# Python Base\n",
            ("python.lint", "1.2.3"): "tampered",
        }
    )

    with pytest.raises(ContentChecksumMismatchError) as exc_info:
        materialize_lockfile(
            target=tmp_path / "skill_demo",
            lockfile=lockfile,
            registry_client=registry_client,
        )

    payload = exc_info.value.to_payload()
    expected_node = next(node for node in lockfile.nodes if node.slug == "python.lint")
    assert payload["slug"] == "python.lint"
    assert payload["version"] == "1.2.3"
    assert payload["algorithm"] == "sha256"
    assert payload["expected_digest"] == expected_node.content_checksum_digest
    assert payload["actual_digest"] == hashlib.sha256(b"tampered").hexdigest()


def test_materialize_lockfile_reuses_precomputed_execution_plan(
    tmp_path, monkeypatch
) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): "# Python Base\n",
        ("python.lint", "1.2.3"): "# Python Lint\n",
    }
    lockfile = _lockfile(content_by_coordinate)
    precomputed_plan = build_execution_plan(lockfile)
    registry_client = FakeRegistryClient(content_by_coordinate)

    def _unexpected_rebuild(_lockfile_arg) -> None:
        raise AssertionError(
            "materialize_lockfile should reuse the precomputed execution plan"
        )

    monkeypatch.setattr(materialize_module, "build_execution_plan", _unexpected_rebuild)

    result = materialize_module.materialize_lockfile(
        target=tmp_path / "skill_demo",
        lockfile=lockfile,
        registry_client=registry_client,
        execution_plan=precomputed_plan,
    )

    assert result.execution_plan == precomputed_plan


def test_build_execution_plan_ignores_selection_explainability_metadata() -> None:
    base_lockfile = _lockfile(
        {
            ("python.base", "1.0.0"): "# Python Base\n",
            ("python.lint", "1.2.3"): "# Python Lint\n",
        }
    )
    low_cost_lock = replace(
        base_lockfile,
        selection=SelectionSnapshot(
            profile="low-cost",
            interaction_mode="never",
            profile_source="cli_override",
            interaction_mode_source="env_override",
        ),
    )
    high_trust_lock = replace(
        base_lockfile,
        selection=SelectionSnapshot(
            profile="high-trust",
            interaction_mode="always",
            profile_source="workspace_config",
            interaction_mode_source="cli_override",
        ),
    )

    assert build_execution_plan(low_cost_lock) == build_execution_plan(high_trust_lock)


def test_write_install_debug_artifacts_writes_graph_trace_and_policy_json(
    tmp_path,
) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): "# Python Base\n",
        ("python.lint", "1.2.3"): "# Python Lint\n",
    }
    graph = ResolutionGraph(
        root=SkillCoordinate(slug="python.lint", version="1.2.3"),
        nodes=[
            _node(
                "python.base", "1.0.0", content_by_coordinate[("python.base", "1.0.0")]
            ),
            _node(
                "python.lint", "1.2.3", content_by_coordinate[("python.lint", "1.2.3")]
            ),
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
        target=tmp_path / "skill_demo",
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
                message="Lifecycle 'published' is allowed.",
                coordinate=SkillCoordinate(slug="python.lint", version="1.2.3"),
            )
        ],
    )

    resolution_dir = tmp_path / "skill_demo" / "resolution"
    assert json.loads((resolution_dir / "graph.json").read_text(encoding="utf-8"))[
        "root"
    ] == {
        "slug": "python.lint",
        "version": "1.2.3",
    }
    assert json.loads((resolution_dir / "trace.json").read_text(encoding="utf-8"))[0][
        "action"
    ] == ("materialize_locked_skill")
    assert json.loads((resolution_dir / "policy.json").read_text(encoding="utf-8"))[0][
        "coordinate"
    ] == {"slug": "python.lint", "version": "1.2.3"}
