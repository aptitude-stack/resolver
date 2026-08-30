from __future__ import annotations

import hashlib
import json
from pathlib import Path

import aptitude_resolver.application.use_cases.install_skill as install_skill_module
import pytest
from aptitude_resolver.application.dto import InstallRequestDto
from aptitude_resolver.application.use_cases import InstallSkillUseCase
from aptitude_resolver.domain.errors import SkillNotFoundError
from aptitude_resolver.lockfile import load_lockfile
from aptitude_resolver.domain.models import (
    DependencySpec,
    DiscoveryQuery,
    SkillCoordinate,
    SkillIdentity,
    SkillMetadata,
    VersionSummary,
)
from tests.unit.artifact_helpers import make_tar_zst


class FakeRegistryClient:
    def __init__(self) -> None:
        self.discovery_by_query: dict[str, list[str]] = {}
        self.identity_by_slug: dict[str, SkillIdentity] = {}
        self.versions_by_slug: dict[str, list[VersionSummary]] = {}
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.dependencies_by_coordinate: dict[
            tuple[str, str], list[DependencySpec]
        ] = {}
        self.artifact_by_coordinate: dict[tuple[str, str], bytes] = {}
        self.discovery_calls: list[DiscoveryQuery] = []
        self.version_calls: list[str] = []
        self.metadata_calls: list[tuple[str, str]] = []
        self.dependency_calls: list[tuple[str, str]] = []
        self.artifact_calls: list[tuple[str, str]] = []

    def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]:
        self.discovery_calls.append(query)
        return list(self.discovery_by_query.get(query.query, []))

    def fetch_skill_identity(self, slug: str) -> SkillIdentity:
        try:
            return self.identity_by_slug[slug]
        except KeyError as exc:
            raise SkillNotFoundError(f"Skill not found: {slug}") from exc

    def list_skill_versions(self, slug: str) -> list[VersionSummary]:
        self.version_calls.append(slug)
        return list(self.versions_by_slug.get(slug, []))

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        self.metadata_calls.append((slug, version))
        return self.metadata_by_coordinate[(slug, version)]

    def fetch_direct_dependencies(
        self, slug: str, version: str
    ) -> list[DependencySpec]:
        self.dependency_calls.append((slug, version))
        return list(self.dependencies_by_coordinate.get((slug, version), []))

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


def test_install_use_case_forwards_cwd_to_discovery_query(tmp_path: Path) -> None:
    use_case = InstallSkillUseCase(FakeRegistryClient(), cwd=tmp_path)

    assert use_case._planner._discover_candidates._cwd == tmp_path


@pytest.mark.parametrize("cancel", [True, False])
def test_install_reviews_the_same_plan_before_any_materialization(tmp_path, cancel):
    registry = FakeRegistryClient()
    _add_independent_skill(
        registry, query="python lint", slug="python-lint", version="1.2.3"
    )
    target = tmp_path / "state"
    previews = []

    def review_plan(plan):
        previews.append(plan)
        assert registry.artifact_calls == []
        assert list(tmp_path.iterdir()) == []
        assert plan.selected_coordinate.slug == "python-lint"
        assert plan.execution_plan is not None
        if cancel:
            raise RuntimeError("declined")
        # A registry change after review must not trigger a second resolution.
        registry.versions_by_slug.clear()

    use_case = InstallSkillUseCase(registry)
    request = InstallRequestDto(query="python lint", target=target, cwd=tmp_path)
    if cancel:
        with pytest.raises(RuntimeError, match="declined"):
            use_case.execute(request, review_plan=review_plan)
        assert list(tmp_path.iterdir()) == []
        assert registry.artifact_calls == []
    else:
        result = use_case.execute(request, review_plan=review_plan)
        assert result.status == "installed"
        assert result.lockfile == previews[0].lockfile
        assert registry.artifact_calls == [("python-lint", "1.2.3")]
    assert len(previews) == 1


def test_cancelled_plan_review_preserves_existing_install_and_lock(tmp_path):
    registry = FakeRegistryClient()
    _add_independent_skill(
        registry, query="python lint", slug="python-lint", version="1.2.3"
    )
    existing_files = [
        tmp_path / "state" / "existing.txt",
        tmp_path / ".codex" / "skills" / "python-lint" / "SKILL.md",
        tmp_path / "aptitude.lock.json",
    ]
    for path in existing_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("existing content", encoding="utf-8")
    before = {path.relative_to(tmp_path): path.read_bytes() for path in existing_files}

    def decline(_plan):
        raise RuntimeError("declined")

    with pytest.raises(RuntimeError, match="declined"):
        InstallSkillUseCase(registry).execute(
            InstallRequestDto(
                query="python lint", target=tmp_path / "state", cwd=tmp_path
            ),
            review_plan=decline,
        )
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert registry.artifact_calls == []


def _artifact(content: str) -> bytes:
    return make_tar_zst({"content.md": content})


def _metadata(slug: str, version: str, *, name: str, artifact: bytes) -> SkillMetadata:
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
        content_checksum_digest=hashlib.sha256(artifact).hexdigest(),
        content_size_bytes=len(artifact),
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
    )


def _version_summary(
    slug: str, version: str, *, name: str, artifact: bytes
) -> VersionSummary:
    return VersionSummary(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=f"{name} description",
        tags=[slug.split(".")[-1]],
        headers={"runtime": "python"},
        rendered_summary=f"{name} summary",
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


def _add_independent_skill(
    registry_client: FakeRegistryClient,
    *,
    query: str,
    slug: str,
    version: str,
) -> None:
    artifact = _artifact(f"# {slug}\n")
    registry_client.discovery_by_query[query] = [slug]
    registry_client.versions_by_slug[slug] = [
        _version_summary(slug, version, name=slug, artifact=artifact)
    ]
    registry_client.metadata_by_coordinate[(slug, version)] = _metadata(
        slug, version, name=slug, artifact=artifact
    )
    registry_client.artifact_by_coordinate[(slug, version)] = artifact


def test_exact_install_bypasses_discovery_and_materializes_requested_slug(
    tmp_path,
) -> None:
    registry_client = FakeRegistryClient()
    slug = "python-lint"
    version = "1.2.3"
    artifact = _artifact("# Python Lint\n")
    registry_client.identity_by_slug[slug] = SkillIdentity(
        slug=slug,
        status="active",
        current_version=SkillCoordinate(slug=slug, version=version),
        current_lifecycle_status="published",
        current_trust_tier="internal",
        current_published_at="2026-03-18T00:00:00Z",
        created_at=None,
        updated_at=None,
    )
    registry_client.versions_by_slug[slug] = [
        _version_summary(slug, version, name="Python Lint", artifact=artifact)
    ]
    registry_client.metadata_by_coordinate[(slug, version)] = _metadata(
        slug, version, name="Python Lint", artifact=artifact
    )
    registry_client.artifact_by_coordinate[(slug, version)] = artifact

    result = InstallSkillUseCase(registry_client).execute(
        InstallRequestDto(
            query=slug,
            exact=True,
            target=tmp_path / "aptitude_state",
            cwd=tmp_path,
        )
    )

    assert result.status == "installed"
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == slug
    assert registry_client.discovery_calls == []


def test_exact_install_missing_requested_version_names_slug_and_version(
    tmp_path,
) -> None:
    class MissingVersionRegistryClient(FakeRegistryClient):
        def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
            try:
                return super().fetch_skill_metadata(slug, version)
            except KeyError as exc:
                raise SkillNotFoundError(
                    f"Skill version not found: {slug}@{version}"
                ) from exc

    registry_client = MissingVersionRegistryClient()
    slug = "python-lint"
    registry_client.identity_by_slug[slug] = SkillIdentity(
        slug=slug,
        status="active",
        current_version=SkillCoordinate(slug=slug, version="1.2.3"),
        current_lifecycle_status="published",
        current_trust_tier="internal",
        current_published_at="2026-03-18T00:00:00Z",
        created_at=None,
        updated_at=None,
    )
    registry_client.versions_by_slug[slug] = [
        _version_summary(
            slug,
            "1.2.3",
            name="Python Lint",
            artifact=_artifact("# Python Lint\n"),
        )
    ]

    with pytest.raises(SkillNotFoundError, match=r"python-lint@9\.9\.9"):
        InstallSkillUseCase(registry_client).execute(
            InstallRequestDto(
                query=slug,
                version="9.9.9",
                exact=True,
                target=tmp_path / "aptitude_state",
                cwd=tmp_path,
            )
        )

    assert registry_client.discovery_calls == []


def test_install_use_case_reuses_one_planned_graph_for_materialization(
    tmp_path,
) -> None:
    registry_client = FakeRegistryClient()
    root_artifact = _artifact("# Python Lint\n")
    dependency_artifact = _artifact("# Python Base\n")

    registry_client.discovery_by_query["python lint"] = ["python-lint"]
    registry_client.versions_by_slug["python-lint"] = [
        _version_summary(
            "python-lint",
            "1.2.3",
            name="Python Lint",
            artifact=root_artifact,
        )
    ]
    registry_client.metadata_by_coordinate[("python-lint", "1.2.3")] = _metadata(
        "python-lint",
        "1.2.3",
        name="Python Lint",
        artifact=root_artifact,
    )
    registry_client.metadata_by_coordinate[("python-base", "1.0.0")] = _metadata(
        "python-base",
        "1.0.0",
        name="Python Base",
        artifact=dependency_artifact,
    )
    registry_client.dependencies_by_coordinate[("python-lint", "1.2.3")] = [
        DependencySpec(slug="python-base", version="1.0.0")
    ]
    registry_client.artifact_by_coordinate[("python-lint", "1.2.3")] = root_artifact
    registry_client.artifact_by_coordinate[("python-base", "1.0.0")] = (
        dependency_artifact
    )

    result = InstallSkillUseCase(registry_client).execute(
        InstallRequestDto(
            query="python lint",
            target=tmp_path / "aptitude_state",
            cwd=tmp_path,
        )
    )

    assert result.status == "installed"
    assert result.lockfile is not None
    assert result.lockfile.root.selected_node_id == "python-lint@1.2.3"
    assert result.execution_plan is not None
    assert [step.node_id for step in result.execution_plan.steps] == [
        "python-base@1.0.0",
        "python-lint@1.2.3",
    ]
    assert registry_client.discovery_calls[0].query == "python lint"
    assert registry_client.version_calls == ["python-lint"]
    assert registry_client.metadata_calls == [
        ("python-lint", "1.2.3"),
        ("python-base", "1.0.0"),
    ]
    assert registry_client.dependency_calls == [
        ("python-lint", "1.2.3"),
        ("python-base", "1.0.0"),
    ]
    assert registry_client.artifact_calls == [
        ("python-base", "1.0.0"),
        ("python-lint", "1.2.3"),
    ]
    resolution_dir = tmp_path / "aptitude_state" / "resolution"
    assert (resolution_dir / "graph.json").exists()
    assert (resolution_dir / "trace.json").exists()
    assert (resolution_dir / "policy.json").exists()
    project_lock_path = tmp_path / "aptitude.lock.json"
    assert result.lock_path == str(project_lock_path)
    assert project_lock_path.exists()
    graph_payload = json.loads(
        (resolution_dir / "graph.json").read_text(encoding="utf-8")
    )
    assert graph_payload["root"] == {"slug": "python-lint", "version": "1.2.3"}
    project_lock_payload = json.loads(project_lock_path.read_text(encoding="utf-8"))
    assert project_lock_payload["root"]["selected_node_id"] == "python-lint@1.2.3"
    assert project_lock_payload["roots"] == [project_lock_payload["root"]]


def test_install_use_case_accumulates_project_lockfile(tmp_path) -> None:
    registry_client = FakeRegistryClient()
    _add_independent_skill(
        registry_client,
        query="python lint",
        slug="python-lint",
        version="1.2.3",
    )
    _add_independent_skill(
        registry_client,
        query="js lint",
        slug="js-lint",
        version="2.1.0",
    )
    use_case = InstallSkillUseCase(registry_client)
    request = {"target": tmp_path / "aptitude_state", "cwd": tmp_path}

    use_case.execute(InstallRequestDto(query="python lint", **request))
    result = use_case.execute(InstallRequestDto(query="js lint", **request))

    assert result.lockfile is not None
    assert [root.selected_node_id for root in result.lockfile.roots] == [
        "python-lint@1.2.3",
        "js-lint@2.1.0",
    ]
    assert [
        root.selected_node_id
        for root in load_lockfile(tmp_path / "aptitude.lock.json").roots
    ] == [root.selected_node_id for root in result.lockfile.roots]


def test_install_use_case_accumulates_global_lockfile(tmp_path, monkeypatch) -> None:
    registry_client = FakeRegistryClient()
    _add_independent_skill(
        registry_client,
        query="python lint",
        slug="python-lint",
        version="1.2.3",
    )
    _add_independent_skill(
        registry_client,
        query="js lint",
        slug="js-lint",
        version="2.1.0",
    )
    global_state_dir = tmp_path / "global-state"
    monkeypatch.setattr(
        install_skill_module, "default_aptitude_state_dir", lambda: global_state_dir
    )
    monkeypatch.setattr(
        install_skill_module, "resolve_agent_install_roots", lambda **_: {}
    )
    use_case = InstallSkillUseCase(registry_client)
    request = {"target": tmp_path / "aptitude_state", "scope": "global"}

    use_case.execute(InstallRequestDto(query="python lint", **request))
    result = use_case.execute(InstallRequestDto(query="js lint", **request))

    lock_path = global_state_dir / "aptitude.lock.json"
    assert result.lock_path == str(lock_path)
    assert [root.selected_node_id for root in load_lockfile(lock_path).roots] == [
        "python-lint@1.2.3",
        "js-lint@2.1.0",
    ]


def test_install_use_case_returns_selection_required_before_dependency_resolution_or_materialization(
    tmp_path,
) -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["python-lint", "js-lint"]
    registry_client.versions_by_slug["python-lint"] = [
        _version_summary(
            "python-lint",
            "1.2.3",
            name="Python Lint",
            artifact=_artifact("# Python Lint\n"),
        )
    ]
    registry_client.versions_by_slug["js-lint"] = [
        _version_summary(
            "js-lint",
            "2.1.0",
            name="JavaScript Lint",
            artifact=_artifact("# JavaScript Lint\n"),
        )
    ]

    result = InstallSkillUseCase(registry_client).execute(
        InstallRequestDto(
            query="lint",
            target=tmp_path / "aptitude_state",
            interaction_mode="always",
            prompt_capable=True,
        )
    )

    assert result.status == "selection_required"
    assert [item.slug for item in result.candidates] == ["python-lint", "js-lint"]
    assert registry_client.dependency_calls == []
    assert registry_client.artifact_calls == []
