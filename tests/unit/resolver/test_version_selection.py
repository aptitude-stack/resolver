from __future__ import annotations

import pytest

from aptitude_client.domain.errors import (
    InteractiveSelectionUnavailableError,
    SelectionSlugNotFoundError,
    SkillNotFoundError,
)
from aptitude_client.domain.models import (
    DiscoveredSkill,
    DiscoveryCandidate,
    SearchIntent,
    SkillCoordinate,
    SkillMetadata,
    VersionSummary,
)
from aptitude_client.resolver.solver import (
    resolve_candidate_versions,
    select_final_candidate,
    select_preferred_version,
)


class FakeRegistryClient:
    def __init__(self) -> None:
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.metadata_calls: list[tuple[str, str]] = []

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        self.metadata_calls.append((slug, version))
        try:
            return self.metadata_by_coordinate[(slug, version)]
        except KeyError as exc:
            raise SkillNotFoundError(f"Skill version not found: {slug}@{version}") from exc



def _version(
    slug: str,
    version: str,
    *,
    name: str = "Python Lint",
    description: str = "Linting skill",
    tags: list[str] | None = None,
    runtime: str = "python",
    trust_tier: str = "internal",
    lifecycle_status: str = "published",
    published_at: str = "2026-03-18T00:00:00Z",
    rendered_summary: str = "Lint Python files.",
    is_current_default: bool = False,
) -> VersionSummary:
    return VersionSummary(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=description,
        tags=tags or ["python", "lint"],
        headers={"runtime": runtime} if runtime else {},
        rendered_summary=rendered_summary,
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
        published_at=published_at,
        is_current_default=is_current_default,
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=256,
        token_estimate=100,
        maturity_score=0.9,
        security_score=0.95,
    )



def _metadata(
    slug: str,
    version: str,
    *,
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
    runtime: str = "python",
) -> SkillMetadata:
    return SkillMetadata(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=description or f"{name} description",
        tags=tags or ["python", "lint"],
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
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
    )



def _intent(query: str, *, language: str | None = None) -> SearchIntent:
    terms = query.split()
    return SearchIntent(
        raw_query=query,
        normalized_query=query,
        terms=terms,
        preferred_tags=list(terms),
        preferred_labels=list(terms),
        language=language,
        trust_preference=None,
    )



def _candidate(slug: str, version: str) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        slug=slug,
        selected_version=_version(slug, version),
        labels=["lint", "python"],
        match_reasons=["server_candidate"],
    )



def test_select_preferred_version_prefers_lifecycle_trust_and_semver() -> None:
    selected = select_preferred_version(
        [
            _version("python.lint", "2.0.0", trust_tier="untrusted"),
            _version("python.lint", "1.9.0", trust_tier="verified"),
            _version("python.lint", "2.1.0", trust_tier="verified", lifecycle_status="deprecated"),
            _version("python.lint", "2.0.1", trust_tier="verified"),
        ]
    )

    assert selected.coordinate.version == "2.0.1"



def test_resolve_candidate_versions_selects_preferred_version_and_enriches_metadata() -> None:
    registry_client = FakeRegistryClient()
    registry_client.metadata_by_coordinate[("python.lint", "1.2.3")] = _metadata(
        "python.lint",
        "1.2.3",
        name="Python Lint",
    )

    candidates, trace = resolve_candidate_versions(
        _intent("python lint", language="python"),
        [
            DiscoveredSkill(
                slug="python.lint",
                available_versions=[
                    _version(
                        "python.lint",
                        "1.0.0",
                        name="",
                        description="",
                        tags=[],
                        runtime="",
                        rendered_summary="",
                        trust_tier="verified",
                    ),
                    _version(
                        "python.lint",
                        "1.2.3",
                        name="",
                        description="",
                        tags=[],
                        runtime="",
                        rendered_summary="",
                        trust_tier="verified",
                        is_current_default=True,
                    ),
                ],
            )
        ],
        registry_client,
    )

    assert [candidate.slug for candidate in candidates] == ["python.lint"]
    assert candidates[0].selected_coordinate.version == "1.2.3"
    assert candidates[0].selected_version.name == "Python Lint"
    assert registry_client.metadata_calls == [("python.lint", "1.2.3")]
    assert [item.action for item in trace] == [
        "select_candidate_version",
        "enrich_candidate_version",
    ]



def test_resolve_candidate_versions_uses_requested_version_and_skips_missing_candidates() -> None:
    registry_client = FakeRegistryClient()
    registry_client.metadata_by_coordinate[("python.lint", "2.0.0")] = _metadata(
        "python.lint",
        "2.0.0",
        name="Python Lint",
    )

    candidates, trace = resolve_candidate_versions(
        _intent("python lint", language="python"),
        [
            DiscoveredSkill(slug="python.lint", available_versions=[_version("python.lint", "1.2.3")]),
            DiscoveredSkill(slug="generic.lint", available_versions=[_version("generic.lint", "3.0.0")]),
        ],
        registry_client,
        version="2.0.0",
    )

    assert [candidate.slug for candidate in candidates] == ["python.lint"]
    assert candidates[0].selected_coordinate.version == "2.0.0"
    assert [item.action for item in trace] == [
        "select_candidate_version",
        "candidate_version_miss",
    ]
    assert trace[1].data["slug"] == "generic.lint"



def test_resolve_candidate_versions_keeps_candidate_matching_details_on_selected_version() -> None:
    registry_client = FakeRegistryClient()

    candidates, _ = resolve_candidate_versions(
        _intent("python lint", language="python"),
        [
            DiscoveredSkill(
                slug="python.lint",
                available_versions=[
                    _version(
                        "python.lint",
                        "1.2.3",
                        name="Python Lint",
                        description="Lint Python code",
                        tags=["python", "lint"],
                        runtime="python",
                        rendered_summary="Lint Python code",
                    )
                ],
            )
        ],
        registry_client,
    )

    assert candidates[0].matched_labels == ["python", "lint"]
    assert candidates[0].match_reasons == [
        "exact_name_match",
        "exact_slug_match",
        "runtime_match",
        "label_overlap",
    ]



def test_select_final_candidate_respects_explicit_slug() -> None:
    result = select_final_candidate(
        query="lint",
        candidates=[_candidate("python.lint", "1.2.3"), _candidate("js.lint", "2.1.0")],
        select_slug="js.lint",
        interaction_mode="never",
        prompt_capable=False,
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.slug == "js.lint"
    assert result.selection_mode == "explicit_slug"
    assert result.trace == []



def test_select_final_candidate_returns_selection_required_for_auto_ambiguity_when_prompt_capable() -> None:
    result = select_final_candidate(
        query="lint",
        candidates=[_candidate("python.lint", "1.2.3"), _candidate("js.lint", "2.1.0")],
        select_slug=None,
        interaction_mode="auto",
        prompt_capable=True,
    )

    assert result.selected_candidate is None
    assert result.selection_mode is None
    assert result.trace == []



def test_select_final_candidate_returns_selection_required_for_always_mode() -> None:
    result = select_final_candidate(
        query="lint",
        candidates=[_candidate("python.lint", "1.2.3"), _candidate("js.lint", "2.1.0")],
        select_slug=None,
        interaction_mode="always",
        prompt_capable=True,
    )

    assert result.selected_candidate is None
    assert result.selection_mode is None
    assert result.trace == []


def test_select_final_candidate_raises_when_always_mode_cannot_prompt() -> None:
    with pytest.raises(InteractiveSelectionUnavailableError):
        select_final_candidate(
            query="lint",
            candidates=[_candidate("python.lint", "1.2.3"), _candidate("js.lint", "2.1.0")],
            select_slug=None,
            interaction_mode="always",
            prompt_capable=False,
        )


def test_select_final_candidate_auto_selects_top_ranked_candidate_when_prompt_unavailable() -> None:
    result = select_final_candidate(
        query="lint",
        candidates=[_candidate("python.lint", "1.2.3"), _candidate("js.lint", "2.1.0")],
        select_slug=None,
        interaction_mode="auto",
        prompt_capable=False,
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.slug == "python.lint"
    assert result.selection_mode == "non_interactive_top_ranked"
    assert [item.action for item in result.trace] == ["auto_select_top_ranked"]


def test_select_final_candidate_never_mode_auto_selects_top_ranked_candidate() -> None:
    result = select_final_candidate(
        query="lint",
        candidates=[_candidate("python.lint", "1.2.3"), _candidate("js.lint", "2.1.0")],
        select_slug=None,
        interaction_mode="never",
        prompt_capable=True,
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.slug == "python.lint"
    assert result.selection_mode == "non_interactive_top_ranked"
    assert [item.action for item in result.trace] == ["auto_select_top_ranked"]



def test_select_final_candidate_raises_when_selected_slug_is_missing() -> None:
    with pytest.raises(SelectionSlugNotFoundError):
        select_final_candidate(
            query="lint",
            candidates=[_candidate("python.lint", "1.2.3")],
            select_slug="js.lint",
            interaction_mode="never",
            prompt_capable=False,
        )
