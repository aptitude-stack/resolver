from __future__ import annotations

import pytest

from aptitude_client.application.dto import ResolveQueryRequestDto
from aptitude_client.application.use_cases import ResolveSkillQueryUseCase
from aptitude_client.domain.errors import (
    DiscoveryNoCandidatesError,
    SelectionSlugNotFoundError,
    SkillNotFoundError,
)
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
        self.discovery_calls: list[DiscoveryQuery] = []
        self.identity_calls: list[str] = []
        self.version_calls: list[str] = []
        self.metadata_calls: list[tuple[str, str]] = []
        self.dependency_calls: list[tuple[str, str]] = []

    def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]:
        self.discovery_calls.append(query)
        return list(self.discovery_by_query.get(query.name, []))

    def fetch_skill_identity(self, slug: str) -> SkillIdentity:
        self.identity_calls.append(slug)
        try:
            return self.identity_by_slug[slug]
        except KeyError as exc:
            raise SkillNotFoundError(f"Skill not found: {slug}") from exc

    def list_skill_versions(self, slug: str) -> list[VersionSummary]:
        self.version_calls.append(slug)
        return list(self.versions_by_slug.get(slug, []))

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        self.metadata_calls.append((slug, version))
        try:
            return self.metadata_by_coordinate[(slug, version)]
        except KeyError as exc:
            raise SkillNotFoundError(f"Skill version not found: {slug}@{version}") from exc

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]:
        self.dependency_calls.append((slug, version))
        return list(self.dependencies_by_coordinate.get((slug, version), []))



def _metadata(
    slug: str,
    version: str,
    *,
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
    runtime: str = "python",
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
) -> SkillMetadata:
    return SkillMetadata(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=description or f"{name} description",
        tags=tags or ["lint"],
        headers={"runtime": runtime},
        inputs_schema={"type": "object"},
        outputs_schema={"type": "object"},
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
        rendered_summary=f"{name} summary",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
        published_at="2026-03-18T00:00:00Z",
    )



def _version_summary(
    slug: str,
    version: str,
    *,
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
    runtime: str = "python",
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
    published_at: str = "2026-03-18T00:00:00Z",
) -> VersionSummary:
    return VersionSummary(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=description or f"{name} description",
        tags=tags or ["lint"],
        headers={"runtime": runtime},
        rendered_summary=f"{name} summary",
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
        published_at=published_at,
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )



def test_query_use_case_resolves_exact_slug_without_discovery() -> None:
    registry_client = FakeRegistryClient()
    registry_client.identity_by_slug["python.lint"] = SkillIdentity(
        slug="python.lint",
        status="active",
        current_version=SkillCoordinate(slug="python.lint", version="1.2.3"),
        current_lifecycle_status="published",
        current_trust_tier="internal",
        current_published_at="2026-03-18T00:00:00Z",
        created_at="2026-03-01T00:00:00Z",
        updated_at="2026-03-18T00:00:00Z",
    )
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary("python.lint", "1.2.3", name="Python Lint")
    ]
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
    )

    result = ResolveSkillQueryUseCase(registry_client).execute(
        ResolveQueryRequestDto(query="python.lint")
    )

    assert registry_client.discovery_calls == []
    assert result.status == "resolved"
    assert result.selection_mode == "single_candidate"
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == "python.lint"
    assert result.lockfile is not None
    assert result.lockfile.root.selected_node_id == "python.lint@1.2.3"
    assert result.execution_plan is not None
    assert [step.node_id for step in result.execution_plan.steps] == ["python.lint@1.2.3"]
    assert any(item.action == "exact_slug_hit" for item in result.trace)



def test_query_use_case_returns_selection_required_for_interactive_ambiguity() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["python lint"] = ["js.lint", "python.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary(
            "python.lint",
            "1.2.3",
            name="Python Lint",
            tags=["python", "lint"],
        )
    ]
    registry_client.versions_by_slug["js.lint"] = [
        _version_summary(
            "js.lint",
            "2.1.0",
            name="JavaScript Lint",
            tags=["javascript", "lint"],
            runtime="javascript",
        )
    ]

    result = ResolveSkillQueryUseCase(registry_client).execute(
        ResolveQueryRequestDto(query="python lint", interactive=True)
    )

    assert result.status == "selection_required"
    assert [item.slug for item in result.candidates] == ["python.lint", "js.lint"]
    assert result.selection_mode is None
    assert registry_client.metadata_calls == []



def test_query_use_case_auto_selects_top_ranked_candidate_when_non_interactive() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["python lint"] = ["js.lint", "python.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary(
            "python.lint",
            "1.2.3",
            name="Python Lint",
            tags=["python", "lint"],
        )
    ]
    registry_client.versions_by_slug["js.lint"] = [
        _version_summary(
            "js.lint",
            "2.1.0",
            name="JavaScript Lint",
            tags=["javascript", "lint"],
            runtime="javascript",
        )
    ]
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
        tags=["python", "lint"],
    )
    registry_client.metadata_by_coordinate[("python.base", "1.0.0")] = _metadata(
        "python.base",
        "1.0.0",
        name="Python Base",
        tags=["python", "base"],
    )
    registry_client.dependencies_by_coordinate[("python.lint", "1.2.3")] = [
        DependencySpec(slug="python.base", version="1.0.0", optional=False, markers=["linux"])
    ]

    result = ResolveSkillQueryUseCase(registry_client).execute(
        ResolveQueryRequestDto(query="python lint")
    )

    assert result.status == "resolved"
    assert result.selection_mode == "non_interactive_top_ranked"
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == "python.lint"
    assert result.graph is not None
    assert [item.slug for item in result.graph.install_order] == ["python.base", "python.lint"]
    assert result.lockfile is not None
    assert result.lockfile.install_order == ["python.base@1.0.0", "python.lint@1.2.3"]
    assert result.execution_plan is not None
    assert [step.node_id for step in result.execution_plan.steps] == [
        "python.base@1.0.0",
        "python.lint@1.2.3",
    ]
    assert any(item.action == "auto_select_top_ranked" for item in result.trace)



def test_query_use_case_respects_explicit_selected_slug() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["python.lint", "js.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary("python.lint", "1.2.3", name="Python Lint")
    ]
    registry_client.versions_by_slug["js.lint"] = [
        _version_summary(
            "js.lint",
            "2.1.0",
            name="JavaScript Lint",
            runtime="javascript",
            tags=["javascript", "lint"],
        )
    ]
    registry_client.metadata_by_coordinate[("js.lint", "2.1.0")] = _metadata(
        "js.lint",
        "2.1.0",
        name="JavaScript Lint",
        runtime="javascript",
        tags=["javascript", "lint"],
    )

    result = ResolveSkillQueryUseCase(registry_client).execute(
        ResolveQueryRequestDto(query="lint", select_slug="js.lint")
    )

    assert result.status == "resolved"
    assert result.selection_mode == "explicit_slug"
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == "js.lint"
    assert result.lockfile is not None
    assert result.lockfile.root.selected_node_id == "js.lint@2.1.0"



def test_query_use_case_raises_when_selected_slug_is_missing_from_candidates() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["python.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary("python.lint", "1.2.3", name="Python Lint")
    ]

    with pytest.raises(SelectionSlugNotFoundError):
        ResolveSkillQueryUseCase(registry_client).execute(
            ResolveQueryRequestDto(query="lint", select_slug="js.lint")
        )



def test_query_use_case_raises_when_discovery_has_no_candidates() -> None:
    with pytest.raises(DiscoveryNoCandidatesError):
        ResolveSkillQueryUseCase(FakeRegistryClient()).execute(
            ResolveQueryRequestDto(query="python lint")
        )
