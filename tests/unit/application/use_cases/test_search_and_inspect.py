from __future__ import annotations

import hashlib

from aptitude_resolver.application.dto import InspectSkillRequestDto, SearchSkillsRequestDto
from aptitude_resolver.application.use_cases import InspectSkillUseCase, SearchSkillsUseCase
from aptitude_resolver.domain.errors import SkillNotFoundError
from aptitude_resolver.domain.models import (
    DiscoveryQuery,
    SkillCoordinate,
    SkillIdentity,
    SkillMetadata,
    VersionSummary,
)
from aptitude_resolver.domain.policy import PolicyContext, SelectionPreferences
from tests.unit.artifact_helpers import make_tar_zst


class FakeRegistryClient:
    def __init__(self) -> None:
        self.discovery_by_query: dict[str, list[str]] = {}
        self.identity_by_slug: dict[str, SkillIdentity] = {}
        self.versions_by_slug: dict[str, list[VersionSummary]] = {}
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.artifact_by_coordinate: dict[tuple[str, str], bytes] = {}
        self.discovery_calls: list[DiscoveryQuery] = []
        self.identity_calls: list[str] = []
        self.version_calls: list[str] = []
        self.metadata_calls: list[tuple[str, str]] = []
        self.artifact_calls: list[tuple[str, str]] = []

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
        return self.metadata_by_coordinate[(slug, version)]

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


def _metadata(slug: str, version: str, *, name: str, artifact: bytes) -> SkillMetadata:
    return SkillMetadata(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=f"{name} description",
        tags=[slug.split(".")[-1]],
        headers={"runtime": "python"},
        inputs_schema={"type": "object"},
        outputs_schema={"type": "object"},
        token_estimate=120,
        maturity_score=0.9,
        security_score=0.95,
        rendered_summary=f"{name} summary",
        content_checksum_algorithm="sha256",
        content_checksum_digest=hashlib.sha256(artifact).hexdigest(),
        content_size_bytes=len(artifact),
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-28T00:00:00Z",
    )


def _version_summary(
    slug: str,
    version: str,
    *,
    name: str,
    artifact: bytes,
    tags: list[str] | None = None,
    runtime: str = "python",
    trust_tier: str = "internal",
    token_estimate: int = 120,
    content_size_bytes: int | None = None,
    published_at: str = "2026-03-28T00:00:00Z",
    is_current_default: bool = False,
) -> VersionSummary:
    return VersionSummary(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=f"{name} description",
        tags=tags or [slug.split(".")[-1]],
        headers={"runtime": runtime},
        rendered_summary=f"{name} summary",
        lifecycle_status="published",
        trust_tier=trust_tier,
        published_at=published_at,
        content_checksum_algorithm="sha256",
        content_checksum_digest=hashlib.sha256(artifact).hexdigest(),
        content_size_bytes=content_size_bytes or len(artifact),
        token_estimate=token_estimate,
        maturity_score=0.9,
        security_score=0.95,
        is_current_default=is_current_default,
    )


def test_search_use_case_returns_ranked_candidates_without_materialization() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["pdf"] = ["pdf.reader", "pdf.forms"]
    registry_client.versions_by_slug["pdf.reader"] = [
        _version_summary(
            "pdf.reader",
            "1.4.0",
            name="PDF Reader",
            artifact=_artifact("# PDF Reader\n"),
            tags=["pdf", "reader"],
            token_estimate=80,
        )
    ]
    registry_client.versions_by_slug["pdf.forms"] = [
        _version_summary(
            "pdf.forms",
            "1.0.0",
            name="PDF Forms",
            artifact=_artifact("# PDF Forms\n"),
            tags=["pdf", "forms"],
            token_estimate=140,
        )
    ]

    result = SearchSkillsUseCase(
        registry_client,
        selection_preferences=SelectionPreferences(profile="low-cost"),
    ).execute(SearchSkillsRequestDto(query="pdf"))

    assert result.status == "found"
    assert [item.slug for item in result.candidates] == ["pdf.reader", "pdf.forms"]
    assert result.candidates[0].token_estimate == 80
    assert registry_client.identity_calls == []
    assert registry_client.metadata_calls == []
    assert registry_client.artifact_calls == []


def test_search_use_case_applies_policy_filtering_before_returning_candidates() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["pdf"] = ["pdf.reader", "pdf.forms"]
    registry_client.versions_by_slug["pdf.reader"] = [
        _version_summary(
            "pdf.reader",
            "1.4.0",
            name="PDF Reader",
            artifact=_artifact("# PDF Reader\n"),
            trust_tier="internal",
        )
    ]
    registry_client.versions_by_slug["pdf.forms"] = [
        _version_summary(
            "pdf.forms",
            "1.0.0",
            name="PDF Forms",
            artifact=_artifact("# PDF Forms\n"),
            trust_tier="verified",
        )
    ]

    result = SearchSkillsUseCase(
        registry_client,
        policy_context=PolicyContext(allowed_trust_tiers=["verified"]),
    ).execute(SearchSkillsRequestDto(query="pdf"))

    assert [item.slug for item in result.candidates] == ["pdf.forms"]


def test_inspect_use_case_returns_full_metadata_version_list_and_preview() -> None:
    registry_client = FakeRegistryClient()
    content = "# PDF Reader\n\nDetailed markdown content.\n"
    registry_client.discovery_by_query["pdf"] = ["pdf.reader"]
    registry_client.versions_by_slug["pdf.reader"] = [
        _version_summary(
            "pdf.reader",
            "1.4.0",
            name="PDF Reader",
            artifact=_artifact(content),
            is_current_default=True,
        ),
        _version_summary(
            "pdf.reader",
            "1.3.0",
            name="PDF Reader",
            artifact=_artifact(content),
            published_at="2026-03-15T00:00:00Z",
        ),
    ]
    registry_client.metadata_by_coordinate[("pdf.reader", "1.4.0")] = _metadata(
        "pdf.reader",
        "1.4.0",
        name="PDF Reader",
        artifact=_artifact(content),
    )
    registry_client.artifact_by_coordinate[("pdf.reader", "1.4.0")] = _artifact(
        content
    )

    result = InspectSkillUseCase(registry_client).execute(
        InspectSkillRequestDto(query="pdf")
    )

    assert result.status == "inspected"
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == "pdf.reader"
    assert registry_client.identity_calls == []
    assert result.skill is not None
    assert result.skill.token_estimate == 120
    assert result.content_preview == content
    assert result.content_preview_truncated is False
    assert [item.version for item in result.available_versions] == ["1.4.0", "1.3.0"]
    assert registry_client.metadata_calls == [("pdf.reader", "1.4.0")]
    assert registry_client.artifact_calls == [("pdf.reader", "1.4.0")]


def test_inspect_use_case_returns_selection_required_when_prompting_is_expected() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["pdf"] = ["pdf.reader", "pdf.forms"]
    registry_client.versions_by_slug["pdf.reader"] = [
        _version_summary(
            "pdf.reader",
            "1.4.0",
            name="PDF Reader",
            artifact=_artifact("# PDF Reader\n"),
        )
    ]
    registry_client.versions_by_slug["pdf.forms"] = [
        _version_summary(
            "pdf.forms",
            "1.0.0",
            name="PDF Forms",
            artifact=_artifact("# PDF Forms\n"),
        )
    ]

    result = InspectSkillUseCase(registry_client).execute(
        InspectSkillRequestDto(
            query="pdf",
            interaction_mode="always",
            prompt_capable=True,
        )
    )

    assert result.status == "selection_required"
    assert [item.slug for item in result.candidates] == ["pdf.forms", "pdf.reader"]
    assert registry_client.metadata_calls == []


def test_inspect_use_case_truncates_preview_when_requested() -> None:
    registry_client = FakeRegistryClient()
    content = "# PDF Reader\n" + ("A" * 50)
    registry_client.discovery_by_query["pdf"] = ["pdf.reader"]
    registry_client.versions_by_slug["pdf.reader"] = [
        _version_summary(
            "pdf.reader",
            "1.4.0",
            name="PDF Reader",
            artifact=_artifact(content),
        )
    ]
    registry_client.metadata_by_coordinate[("pdf.reader", "1.4.0")] = _metadata(
        "pdf.reader",
        "1.4.0",
        name="PDF Reader",
        artifact=_artifact(content),
    )
    registry_client.artifact_by_coordinate[("pdf.reader", "1.4.0")] = _artifact(
        content
    )

    result = InspectSkillUseCase(registry_client).execute(
        InspectSkillRequestDto(query="pdf", preview_char_limit=20)
    )

    assert result.status == "inspected"
    assert result.content_preview_truncated is True
    assert result.content_preview == "# PDF Reader\nAAAA..."
