from __future__ import annotations

import hashlib
import json

from aptitude_client.application.dto import InstallRequestDto
from aptitude_client.application.use_cases import InstallSkillUseCase
from aptitude_client.domain.errors import SkillNotFoundError
from aptitude_client.domain.models import (
    DependencySpec,
    DiscoveryQuery,
    SkillCoordinate,
    SkillIdentity,
    SkillMetadata,
    VersionSummary,
)


class FakeRegistryClient:
    def __init__(self) -> None:
        self.discovery_by_query: dict[str, list[str]] = {}
        self.identity_by_slug: dict[str, SkillIdentity] = {}
        self.versions_by_slug: dict[str, list[VersionSummary]] = {}
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.dependencies_by_coordinate: dict[tuple[str, str], list[DependencySpec]] = {}
        self.content_by_coordinate: dict[tuple[str, str], str] = {}
        self.discovery_calls: list[DiscoveryQuery] = []
        self.version_calls: list[str] = []
        self.metadata_calls: list[tuple[str, str]] = []
        self.dependency_calls: list[tuple[str, str]] = []
        self.content_calls: list[tuple[str, str]] = []

    def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]:
        self.discovery_calls.append(query)
        return list(self.discovery_by_query.get(query.name, []))

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

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]:
        self.dependency_calls.append((slug, version))
        return list(self.dependencies_by_coordinate.get((slug, version), []))

    def fetch_skill_content(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> str:
        self.content_calls.append((slug, version))
        return self.content_by_coordinate[(slug, version)]



def _metadata(slug: str, version: str, *, name: str, content: str) -> SkillMetadata:
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
        content_checksum_digest=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        content_size_bytes=len(content.encode("utf-8")),
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
    )



def _version_summary(slug: str, version: str, *, name: str, content: str) -> VersionSummary:
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
        content_checksum_digest=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        content_size_bytes=len(content.encode("utf-8")),
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )



def test_install_use_case_reuses_one_planned_graph_for_materialization(tmp_path) -> None:
    registry_client = FakeRegistryClient()
    root_content = "# Python Lint\n"
    dependency_content = "# Python Base\n"

    registry_client.discovery_by_query["python lint"] = ["python.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary(
            "python.lint",
            "1.2.3",
            name="Python Lint",
            content=root_content,
        )
    ]
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
        content=root_content,
    )
    registry_client.metadata_by_coordinate[("python.base", "1.0.0")] = _metadata(
        "python.base",
        "1.0.0",
        name="Python Base",
        content=dependency_content,
    )
    registry_client.dependencies_by_coordinate[("python.lint", "1.2.3")] = [
        DependencySpec(slug="python.base", version="1.0.0")
    ]
    registry_client.content_by_coordinate[("python.lint", "1.2.3")] = root_content
    registry_client.content_by_coordinate[("python.base", "1.0.0")] = dependency_content

    result = InstallSkillUseCase(registry_client).execute(
        InstallRequestDto(
            query="python lint",
            target=tmp_path / "skill_demo",
        )
    )

    assert result.status == "installed"
    assert result.lockfile is not None
    assert result.lockfile.root.selected_node_id == "python.lint@1.2.3"
    assert result.execution_plan is not None
    assert [step.node_id for step in result.execution_plan.steps] == [
        "python.base@1.0.0",
        "python.lint@1.2.3",
    ]
    assert registry_client.discovery_calls[0].name == "python lint"
    assert registry_client.version_calls == ["python.lint"]
    assert registry_client.metadata_calls == [
        ("python.lint", "1.2.3"),
        ("python.base", "1.0.0"),
    ]
    assert registry_client.dependency_calls == [
        ("python.lint", "1.2.3"),
        ("python.base", "1.0.0"),
    ]
    assert registry_client.content_calls == [
        ("python.base", "1.0.0"),
        ("python.lint", "1.2.3"),
    ]
    resolution_dir = tmp_path / "skill_demo" / "resolution"
    assert (resolution_dir / "graph.json").exists()
    assert (resolution_dir / "trace.json").exists()
    assert (resolution_dir / "policy.json").exists()
    graph_payload = json.loads((resolution_dir / "graph.json").read_text(encoding="utf-8"))
    assert graph_payload["root"] == {"slug": "python.lint", "version": "1.2.3"}


def test_install_use_case_returns_selection_required_before_dependency_resolution_or_materialization(
    tmp_path,
) -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["python.lint", "js.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary("python.lint", "1.2.3", name="Python Lint", content="# Python Lint\n")
    ]
    registry_client.versions_by_slug["js.lint"] = [
        _version_summary("js.lint", "2.1.0", name="JavaScript Lint", content="# JavaScript Lint\n")
    ]

    result = InstallSkillUseCase(registry_client).execute(
        InstallRequestDto(
            query="lint",
            target=tmp_path / "skill_demo",
            interaction_mode="always",
            prompt_capable=True,
        )
    )

    assert result.status == "selection_required"
    assert [item.slug for item in result.candidates] == ["python.lint", "js.lint"]
    assert registry_client.dependency_calls == []
    assert registry_client.content_calls == []
