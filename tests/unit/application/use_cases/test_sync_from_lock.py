from __future__ import annotations

import hashlib
import json

import pytest

from aptitude_resolver.application.dto import SyncRequestDto
from aptitude_resolver.application.use_cases import SyncFromLockUseCase
from aptitude_resolver.domain.errors import InvalidLockfileError
from aptitude_resolver.domain.models import (
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
)
from aptitude_resolver.domain.policy import SelectionPreferences
from aptitude_resolver.lockfile import build_lockfile, serialize_lockfile
from tests.unit.artifact_helpers import make_tar_zst


class FakeRegistryClient:
    def __init__(self, artifact_by_coordinate: dict[tuple[str, str], bytes]) -> None:
        self.artifact_by_coordinate = artifact_by_coordinate
        self.artifact_calls: list[tuple[str, str]] = []

    def fetch_skill_artifact(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> bytes:
        self.artifact_calls.append((slug, version))
        return self.artifact_by_coordinate[(slug, version)]


def _artifact(content: str) -> bytes:
    return make_tar_zst({"content.md": content})


def _node(slug: str, version: str, artifact: bytes) -> ResolvedSkillNode:
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
        content_checksum_digest=hashlib.sha256(artifact).hexdigest(),
        content_size_bytes=len(artifact),
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )


def test_sync_from_lock_use_case_materializes_from_lock_only(tmp_path) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
    }
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
    lock_path = tmp_path / "aptitude.lock.json"
    lock_path.write_text(
        serialize_lockfile(
            build_lockfile(
                graph=graph,
                requested_query="python lint",
                requested_version=None,
                selection_mode="single_candidate",
                policy_evaluations=[],
            )
        ),
        encoding="utf-8",
    )

    registry_client = FakeRegistryClient(content_by_coordinate)
    result = SyncFromLockUseCase(registry_client).execute(
        SyncRequestDto(
            lock_path=lock_path,
            target=tmp_path / "skill_demo",
        )
    )

    assert result.status == "synced"
    assert result.lock_path == str(lock_path.resolve())
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == "python.lint"
    assert [step.node_id for step in result.execution_plan.steps] == [
        "python.base@1.0.0",
        "python.lint@1.2.3",
    ]
    assert registry_client.artifact_calls == [
        ("python.base", "1.0.0"),
        ("python.lint", "1.2.3"),
    ]
    assert any(item.action == "load_lockfile" for item in result.trace)


def test_sync_from_lock_use_case_raises_for_missing_lockfile(tmp_path) -> None:
    with pytest.raises(InvalidLockfileError, match="Lockfile not found"):
        SyncFromLockUseCase(FakeRegistryClient({})).execute(
            SyncRequestDto(
                lock_path=tmp_path / "missing.lock.json",
                target=tmp_path / "skill_demo",
            )
        )


def test_sync_from_lock_use_case_does_not_require_selection_metadata(tmp_path) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
    }
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
    lock_payload = json.loads(
        serialize_lockfile(
            build_lockfile(
                graph=graph,
                requested_query="python lint",
                requested_version=None,
                selection_mode="single_candidate",
                policy_evaluations=[],
                selection_preferences=SelectionPreferences(
                    profile="low-cost",
                    interaction_mode="never",
                    profile_source="cli_override",
                    interaction_mode_source="env_override",
                ),
            )
        )
    )
    lock_payload.pop("selection", None)

    lock_path = tmp_path / "aptitude.lock.json"
    lock_path.write_text(json.dumps(lock_payload, indent=2), encoding="utf-8")

    registry_client = FakeRegistryClient(content_by_coordinate)
    result = SyncFromLockUseCase(registry_client).execute(
        SyncRequestDto(
            lock_path=lock_path,
            target=tmp_path / "skill_demo",
        )
    )

    assert result.status == "synced"
    assert registry_client.artifact_calls == [
        ("python.base", "1.0.0"),
        ("python.lint", "1.2.3"),
    ]
    assert result.lockfile is not None
    assert result.lockfile.selection is None
