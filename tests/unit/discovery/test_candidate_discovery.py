from __future__ import annotations

from aptitude_resolver.discovery import DiscoverSkillCandidatesQuery
from aptitude_resolver.domain.models import SkillCoordinate, SkillIdentity, VersionSummary


class FakeRegistryClient:
    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates

    def discover_candidate_slugs(self, query) -> list[str]:
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
    candidates = [f"skill.{index:02d}" for index in range(12)]

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
