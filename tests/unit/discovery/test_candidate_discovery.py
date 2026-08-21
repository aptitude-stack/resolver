from __future__ import annotations

import pytest

import aptitude_resolver.discovery.candidate_discovery as candidate_discovery_module
from aptitude_resolver.discovery import DiscoverSkillCandidatesQuery
from aptitude_resolver.domain.errors import SkillNotFoundError
from aptitude_resolver.domain.models import (
    DiscoveryQuery,
    SkillCoordinate,
    SkillIdentity,
    VersionSummary,
)


class FakeRegistryClient:
    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        self.discovery_calls: list[DiscoveryQuery] = []

    def discover_candidate_slugs(self, query) -> list[str]:
        self.discovery_calls.append(query)
        return list(self.candidates)

    def fetch_skill_identity(self, slug: str) -> SkillIdentity:
        return SkillIdentity(
            slug=slug,
            status="active",
            current_version=SkillCoordinate(slug=slug, version="1.0.0"),
            current_lifecycle_status="published",
            current_trust_tier="internal",
            current_published_at="2026-03-18T00:00:00Z",
            created_at=None,
            updated_at=None,
        )

    def list_skill_versions(self, slug: str) -> list[VersionSummary]:
        return [
            VersionSummary(
                coordinate=SkillCoordinate(slug=slug, version="1.0.0"),
                name=slug,
                description=f"{slug} description",
                tags=["demo"],
                headers={"runtime": "python"},
                rendered_summary=f"{slug} summary",
                lifecycle_status="published",
                trust_tier="internal",
                published_at="2026-03-18T00:00:00Z",
            )
        ]


def test_discovery_keeps_all_registry_candidates_without_client_side_cap() -> None:
    candidates = [f"skill-{index:02d}" for index in range(12)]

    result = DiscoverSkillCandidatesQuery(FakeRegistryClient(candidates)).execute(
        "demo skill"
    )

    assert [match.slug for match in result.matches] == candidates
    discovery_trace = next(
        item for item in result.trace if item.action == "discover_candidates"
    )
    assert discovery_trace.data == {
        "candidate_count": 12,
        "slugs": candidates,
    }


@pytest.mark.parametrize("query", ["lint", "python-lint"])
def test_discovery_posts_every_query_to_registry_discovery(query: str) -> None:
    registry_client = FakeRegistryClient([query])

    result = DiscoverSkillCandidatesQuery(registry_client).execute(query)

    assert [match.slug for match in result.matches] == [query]
    assert [call.query for call in registry_client.discovery_calls] == [query]


def test_exact_discovery_does_not_fall_back_when_slug_is_missing() -> None:
    class MissingSlugRegistryClient(FakeRegistryClient):
        def fetch_skill_identity(self, slug: str) -> SkillIdentity:
            raise SkillNotFoundError(f"Skill not found: {slug}")

    registry_client = MissingSlugRegistryClient(["fallback-skill"])

    with pytest.raises(SkillNotFoundError, match="python-missing"):
        DiscoverSkillCandidatesQuery(registry_client).execute(
            "python-missing", exact=True
        )

    assert registry_client.discovery_calls == []


def test_exact_discovery_skips_advisory_lock_context_loading(monkeypatch) -> None:
    registry_client = FakeRegistryClient(["python-lint"])
    monkeypatch.setattr(
        candidate_discovery_module,
        "load_discovery_context",
        lambda **_: pytest.fail("exact discovery should not load advisory context"),
    )

    result = DiscoverSkillCandidatesQuery(registry_client).execute(
        "python-lint", exact=True
    )

    assert [match.slug for match in result.matches] == ["python-lint"]
