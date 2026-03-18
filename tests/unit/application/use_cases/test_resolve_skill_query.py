from __future__ import annotations

import pytest

from aptitude_client.application.dto import ResolveQueryRequestDto
from aptitude_client.application.use_cases import ResolveSkillQueryUseCase
from aptitude_client.domain.errors import (
    DiscoveryAmbiguousMatchError,
    DiscoveryNoCandidatesError,
    SkillNotFoundError,
    VersionSelectionUnavailableError,
)
from aptitude_client.domain.models import DependencySpec, SkillCoordinate, SkillMetadata


class FakeRegistryClient:
    def __init__(self) -> None:
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.dependencies_by_coordinate: dict[tuple[str, str], list[DependencySpec]] = {}
        self.discovery_by_query: dict[str, list[str]] = {}
        self.metadata_calls: list[tuple[str, str]] = []
        self.dependency_calls: list[tuple[str, str]] = []
        self.discovery_calls: list[str] = []

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        self.metadata_calls.append((slug, version))
        try:
            return self.metadata_by_coordinate[(slug, version)]
        except KeyError as exc:
            raise SkillNotFoundError(f"Skill version not found: {slug}@{version}") from exc

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]:
        self.dependency_calls.append((slug, version))
        return list(self.dependencies_by_coordinate.get((slug, version), []))

    def discover_candidates(self, query: str) -> list[str]:
        self.discovery_calls.append(query)
        return list(self.discovery_by_query.get(query, []))


def _metadata(slug: str, version: str, *, name: str) -> SkillMetadata:
    return SkillMetadata(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=f"{name} description",
        tags=["integration"],
        rendered_summary=f"{name} summary",
        content_checksum_algorithm="sha256",
        content_checksum_digest="abc123",
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
    )


def test_query_use_case_resolves_exact_slug_without_discovery() -> None:
    registry_client = FakeRegistryClient()
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
    )

    result = ResolveSkillQueryUseCase(registry_client).execute(
        ResolveQueryRequestDto(query="python.lint", version="1.2.3")
    )

    assert registry_client.discovery_calls == []
    assert result.selected_coordinate.slug == "python.lint"
    assert result.resolution_strategy is None
    assert result.requested_query is None


def test_query_use_case_resolves_single_discovery_candidate() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["Python Lint"] = ["python.lint"]
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
    )
    registry_client.dependencies_by_coordinate[("python.lint", "1.2.3")] = [
        DependencySpec(slug="python.base", version="1.0.0", optional=False, markers=["linux"])
    ]

    result = ResolveSkillQueryUseCase(registry_client).execute(
        ResolveQueryRequestDto(query="Python Lint", version="1.2.3")
    )

    assert registry_client.discovery_calls == ["Python Lint"]
    assert result.requested_query == "Python Lint"
    assert result.selected_coordinate.slug == "python.lint"
    assert result.resolution_strategy == "discovery"
    assert result.dependencies[0].slug == "python.base"


def test_query_use_case_requires_version_for_discovery_driven_resolution() -> None:
    use_case = ResolveSkillQueryUseCase(FakeRegistryClient())

    with pytest.raises(VersionSelectionUnavailableError):
        use_case.execute(ResolveQueryRequestDto(query="Python Lint", version=None))


def test_query_use_case_raises_when_discovery_has_no_candidates() -> None:
    use_case = ResolveSkillQueryUseCase(FakeRegistryClient())

    with pytest.raises(DiscoveryNoCandidatesError):
        use_case.execute(ResolveQueryRequestDto(query="Python Lint", version="1.2.3"))


def test_query_use_case_raises_when_discovery_is_ambiguous() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["python.lint", "js.lint"]
    use_case = ResolveSkillQueryUseCase(registry_client)

    with pytest.raises(DiscoveryAmbiguousMatchError) as exc_info:
        use_case.execute(ResolveQueryRequestDto(query="lint", version="1.2.3"))

    assert exc_info.value.candidates == ["js.lint", "python.lint"]
