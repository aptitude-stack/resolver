from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile
import threading
import time
from dataclasses import replace

import pytest
import aptitude_resolver.execution.materialize as materialize_module

from aptitude_resolver.domain.errors import (
    ContentChecksumMismatchError,
    InvalidArtifactError,
)
from aptitude_resolver.domain.models import (
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
)
from aptitude_resolver.domain.policy import PolicyEvaluation
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.execution import (
    MaterializationOptions,
    build_execution_plan,
    materialize_lockfile,
    write_install_debug_artifacts,
)
from aptitude_resolver.execution.archive import preview_tar_zstd_artifact
from aptitude_resolver.lockfile import SelectionSnapshot, build_lockfile, load_lockfile
from tests.unit.artifact_helpers import compress_zstd, make_tar_zst


class FakeRegistryClient:
    def __init__(self, artifact_by_coordinate: dict[tuple[str, str], bytes]) -> None:
        self.artifact_by_coordinate = artifact_by_coordinate
        self.calls: list[tuple[str, str]] = []

    def fetch_skill_artifact(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> bytes:
        self.calls.append((slug, version))
        return self.artifact_by_coordinate[(slug, version)]


class DelayedRegistryClient(FakeRegistryClient):
    def __init__(
        self,
        artifact_by_coordinate: dict[tuple[str, str], bytes],
        *,
        delays_by_slug: dict[str, float] | None = None,
    ) -> None:
        super().__init__(artifact_by_coordinate)
        self.delays_by_slug = delays_by_slug or {}
        self._lock = threading.Lock()
        self.active_calls = 0
        self.max_active_calls = 0

    def fetch_skill_artifact(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> bytes:
        with self._lock:
            self.calls.append((slug, version))
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            time.sleep(self.delays_by_slug.get(slug, 0.02))
            return self.artifact_by_coordinate[(slug, version)]
        finally:
            with self._lock:
                self.active_calls -= 1


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


def _artifact(content: str, **extra_files: str | bytes) -> bytes:
    return make_tar_zst({"content.md": content, **extra_files})


def _single_member_tar_zst(
    name: str,
    payload: bytes = b"unsafe",
    *,
    member_type: bytes = tarfile.REGTYPE,
    linkname: str = "",
) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.type = member_type
        info.linkname = linkname
        if member_type == tarfile.REGTYPE:
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        else:
            archive.addfile(info)
    return compress_zstd(tar_buffer.getvalue())


def _lockfile(artifact_by_coordinate: dict[tuple[str, str], bytes]):
    dependency = SkillCoordinate(slug="python.base", version="1.0.0")
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(
                dependency.slug,
                dependency.version,
                artifact_by_coordinate[(dependency.slug, dependency.version)],
            ),
            _node(
                root.slug,
                root.version,
                artifact_by_coordinate[(root.slug, root.version)],
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


def _multi_lockfile(artifact_by_coordinate: dict[tuple[str, str], bytes]):
    base = SkillCoordinate(slug="python.base", version="1.0.0")
    format_skill = SkillCoordinate(slug="python.format", version="2.0.0")
    root = SkillCoordinate(slug="python.lint", version="1.2.3")
    graph = ResolutionGraph(
        root=root,
        nodes=[
            _node(
                base.slug,
                base.version,
                artifact_by_coordinate[(base.slug, base.version)],
            ),
            _node(
                format_skill.slug,
                format_skill.version,
                artifact_by_coordinate[(format_skill.slug, format_skill.version)],
            ),
            _node(
                root.slug,
                root.version,
                artifact_by_coordinate[(root.slug, root.version)],
            ),
        ],
        edges=[
            DependencyEdge(source=root, target=base),
            DependencyEdge(source=root, target=format_skill),
        ],
        install_order=[base, format_skill, root],
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
            ("python.base", "1.0.0"): _artifact("# Python Base\n"),
            ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
        }
    )

    execution_plan = build_execution_plan(lockfile)

    assert [step.node_id for step in execution_plan.steps] == [
        "python.base@1.0.0",
        "python.lint@1.2.3",
    ]


def test_materialize_lockfile_writes_skills_and_resolution_artifacts(tmp_path) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.lint", "1.2.3"): _artifact(
            "# Python Lint\n",
            **{"scripts/setup.py": "print('setup')\n"},
        ),
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
    assert [item.slug for item in result.installed_skills] == [
        "python.base",
        "python.lint",
    ]
    assert (
        materialized_root / "skills" / "python.lint" / "1.2.3" / "content.md"
    ).read_text(encoding="utf-8") == "# Python Lint\n"
    assert (
        materialized_root
        / "skills"
        / "python.lint"
        / "1.2.3"
        / "scripts"
        / "setup.py"
    ).read_text(encoding="utf-8") == "print('setup')\n"
    loaded_lockfile = load_lockfile(
        materialized_root / "resolution" / "aptitude.lock.json"
    )
    assert loaded_lockfile == lockfile
    assert [item.action for item in result.trace] == [
        "materialize_locked_skill",
        "materialize_locked_skill",
    ]
    assert result.installed_skills[0].install_path == str(
        materialized_root / "skills" / "python.base" / "1.0.0"
    )
    assert result.installed_skills[1].install_path == str(
        materialized_root / "skills" / "python.lint" / "1.2.3"
    )
    assert result.trace[0].data["install_path"] == str(
        materialized_root / "skills" / "python.base" / "1.0.0"
    )


def test_materialize_lockfile_preserves_existing_target_when_promotion_fails(
    tmp_path,
    monkeypatch,
) -> None:
    target = tmp_path / "skill_demo"
    target.mkdir()
    (target / "keep.txt").write_text("keep me\n", encoding="utf-8")
    (target / "locked.txt").write_text("locked\n", encoding="utf-8")
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
    }
    lockfile = _lockfile(content_by_coordinate)
    registry_client = FakeRegistryClient(content_by_coordinate)
    original_rmtree = materialize_module.shutil.rmtree
    original_replace = Path.replace

    def _partial_delete_then_fail(path, *args, **kwargs):
        if Path(path) == target:
            (target / "locked.txt").unlink()
            raise PermissionError("target contains a locked file")
        return original_rmtree(path, *args, **kwargs)

    def _fail_target_move(self, target_path):
        if self == target:
            raise PermissionError("target contains a locked file")
        return original_replace(self, target_path)

    monkeypatch.setattr(materialize_module.shutil, "rmtree", _partial_delete_then_fail)
    monkeypatch.setattr(Path, "replace", _fail_target_move)

    with pytest.raises(PermissionError, match="locked file"):
        materialize_lockfile(
            target=target,
            lockfile=lockfile,
            registry_client=registry_client,
        )

    assert (target / "keep.txt").read_text(encoding="utf-8") == "keep me\n"
    assert (target / "locked.txt").read_text(encoding="utf-8") == "locked\n"


def test_preview_tar_zstd_artifact_reads_skill_markdown_bundle_entry() -> None:
    artifact = make_tar_zst({"skill-bundle/SKILL.md": "# Python Base Runtime\n"})

    preview, truncated = preview_tar_zstd_artifact(
        slug="python.base",
        version="1.1.0",
        artifact=artifact,
        limit=100,
    )

    assert preview == "# Python Base Runtime\n"
    assert truncated is False


def test_materialize_lockfile_raises_when_checksum_does_not_match(tmp_path) -> None:
    lockfile = _lockfile(
        {
            ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
            ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        }
    )
    registry_client = FakeRegistryClient(
        {
            ("python.base", "1.0.0"): _artifact("# Python Base\n"),
            ("python.lint", "1.2.3"): b"tampered",
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
    assert not (tmp_path / "skill_demo").exists()


@pytest.mark.parametrize(
    ("artifact", "message"),
    [
        (_single_member_tar_zst("../escape.txt"), "unsafe path segment"),
        (
            _single_member_tar_zst(
                "linked.txt",
                member_type=tarfile.SYMTYPE,
                linkname="content.md",
            ),
            "not a regular file or directory",
        ),
    ],
)
def test_materialize_lockfile_rejects_unsafe_archive_members(
    tmp_path,
    artifact: bytes,
    message: str,
) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.lint", "1.2.3"): artifact,
    }
    lockfile = _lockfile(content_by_coordinate)
    registry_client = FakeRegistryClient(content_by_coordinate)

    with pytest.raises(InvalidArtifactError, match=message):
        materialize_lockfile(
            target=tmp_path / "skill_demo",
            lockfile=lockfile,
            registry_client=registry_client,
        )

    assert not (tmp_path / "skill_demo").exists()


def test_materialize_lockfile_downloads_locked_artifacts_in_parallel(
    tmp_path,
) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.format", "2.0.0"): _artifact("# Python Format\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
    }
    registry_client = DelayedRegistryClient(content_by_coordinate)
    lockfile = _multi_lockfile(content_by_coordinate)

    materialize_lockfile(
        target=tmp_path / "skill_demo",
        lockfile=lockfile,
        registry_client=registry_client,
        options=MaterializationOptions(concurrent_downloads=3, concurrent_installs=1),
    )

    assert registry_client.max_active_calls > 1


def test_materialize_lockfile_preserves_lock_order_when_workers_finish_out_of_order(
    tmp_path,
) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.format", "2.0.0"): _artifact("# Python Format\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
    }
    registry_client = DelayedRegistryClient(
        content_by_coordinate,
        delays_by_slug={
            "python.base": 0.05,
            "python.format": 0.01,
            "python.lint": 0.02,
        },
    )
    lockfile = _multi_lockfile(content_by_coordinate)

    result = materialize_lockfile(
        target=tmp_path / "skill_demo",
        lockfile=lockfile,
        registry_client=registry_client,
        options=MaterializationOptions(concurrent_downloads=3, concurrent_installs=3),
    )

    assert [item.slug for item in result.installed_skills] == [
        "python.base",
        "python.format",
        "python.lint",
    ]
    assert [item.data["node_id"] for item in result.trace] == [
        "python.base@1.0.0",
        "python.format@2.0.0",
        "python.lint@1.2.3",
    ]


def test_materialize_lockfile_concurrent_downloads_one_is_serial(tmp_path) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.format", "2.0.0"): _artifact("# Python Format\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
    }
    registry_client = DelayedRegistryClient(content_by_coordinate)
    lockfile = _multi_lockfile(content_by_coordinate)

    materialize_lockfile(
        target=tmp_path / "skill_demo",
        lockfile=lockfile,
        registry_client=registry_client,
        options=MaterializationOptions(concurrent_downloads=1, concurrent_installs=3),
    )

    assert registry_client.max_active_calls == 1
    assert registry_client.calls == [
        ("python.base", "1.0.0"),
        ("python.format", "2.0.0"),
        ("python.lint", "1.2.3"),
    ]


def test_materialize_lockfile_concurrent_installs_one_serializes_extraction(
    tmp_path,
    monkeypatch,
) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.format", "2.0.0"): _artifact("# Python Format\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
    }
    registry_client = DelayedRegistryClient(content_by_coordinate)
    lockfile = _multi_lockfile(content_by_coordinate)
    lock = threading.Lock()
    active_extracts = 0
    max_active_extracts = 0
    extract_order: list[str] = []

    def _delayed_extract(*, node, artifact, target_dir) -> list[str]:
        nonlocal active_extracts, max_active_extracts
        with lock:
            active_extracts += 1
            max_active_extracts = max(max_active_extracts, active_extracts)
            extract_order.append(node.slug)
        try:
            time.sleep(0.02)
            target_dir.mkdir(parents=True, exist_ok=True)
            return ["content.md"]
        finally:
            with lock:
                active_extracts -= 1

    monkeypatch.setattr(
        materialize_module,
        "extract_tar_zstd_artifact",
        _delayed_extract,
    )

    materialize_lockfile(
        target=tmp_path / "skill_demo",
        lockfile=lockfile,
        registry_client=registry_client,
        options=MaterializationOptions(concurrent_downloads=3, concurrent_installs=1),
    )

    assert max_active_extracts == 1
    assert extract_order == ["python.base", "python.format", "python.lint"]


def test_default_install_worker_count_is_capped_at_four(monkeypatch) -> None:
    monkeypatch.setattr(materialize_module.os, "cpu_count", lambda: 8)

    assert (
        materialize_module._resolve_install_worker_count(
            MaterializationOptions(),
            artifact_count=10,
        )
        == 4
    )


def test_materialize_lockfile_reuses_precomputed_execution_plan(
    tmp_path, monkeypatch
) -> None:
    content_by_coordinate = {
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
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
            ("python.base", "1.0.0"): _artifact("# Python Base\n"),
            ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
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
        ("python.base", "1.0.0"): _artifact("# Python Base\n"),
        ("python.lint", "1.2.3"): _artifact("# Python Lint\n"),
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
