from __future__ import annotations

import pytest

from aptitude_client.application.dto import InstallRequestDto, ResolveQueryRequestDto
from aptitude_client.application.use_cases import InstallSkillUseCase, ResolveSkillQueryUseCase
from aptitude_client.domain.errors import SkillNotFoundError
from aptitude_client.domain.models import DiscoveryQuery, SkillIdentity, VersionSummary


class FakeRegistryClient:
    def __init__(self) -> None:
        self.discovery_calls: list[DiscoveryQuery] = []
        self.identity_calls: list[str] = []

    def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]:
        self.discovery_calls.append(query)
        return []

    def fetch_skill_identity(self, slug: str) -> SkillIdentity:
        self.identity_calls.append(slug)
        raise SkillNotFoundError(f"Skill not found: {slug}")

    def list_skill_versions(self, slug: str) -> list[VersionSummary]:
        raise AssertionError("list_skill_versions should not be called for a missing explicit dotted slug")

    def fetch_skill_metadata(self, slug: str, version: str):
        raise AssertionError("fetch_skill_metadata should not be called for a missing explicit dotted slug")

    def fetch_direct_dependencies(self, slug: str, version: str):
        raise AssertionError("fetch_direct_dependencies should not be called for a missing explicit dotted slug")

    def fetch_skill_content(self, slug: str, version: str) -> str:
        raise AssertionError("fetch_skill_content should not be called for a missing explicit dotted slug")


def test_resolve_use_case_raises_skill_not_found_for_missing_explicit_dotted_slug() -> None:
    registry_client = FakeRegistryClient()

    with pytest.raises(
        SkillNotFoundError,
        match="Skill not found: postman.primary.1773823396197-11603",
    ):
        ResolveSkillQueryUseCase(registry_client).execute(
            ResolveQueryRequestDto(query="postman.primary.1773823396197-11603")
        )

    assert registry_client.identity_calls == ["postman.primary.1773823396197-11603"]
    assert registry_client.discovery_calls == []


def test_install_use_case_raises_skill_not_found_for_missing_explicit_dotted_slug(tmp_path) -> None:
    registry_client = FakeRegistryClient()

    with pytest.raises(
        SkillNotFoundError,
        match="Skill not found: postman.primary.1773823396197-11603",
    ):
        InstallSkillUseCase(registry_client).execute(
            InstallRequestDto(
                query="postman.primary.1773823396197-11603",
                target=tmp_path / "skill_demo",
            )
        )

    assert registry_client.identity_calls == ["postman.primary.1773823396197-11603"]
    assert registry_client.discovery_calls == []
