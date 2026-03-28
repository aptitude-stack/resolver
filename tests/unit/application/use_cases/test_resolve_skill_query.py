from __future__ import annotations

import pytest

from aptitude_client.application.dto import ResolveQueryRequestDto
from aptitude_client.application.use_cases import ResolveSkillQueryUseCase
from aptitude_client.domain.errors import (
    DiscoveryNoCandidatesError,
    InteractiveSelectionUnavailableError,
    PolicyViolationError,
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
from aptitude_client.domain.policy import PolicyContext
from aptitude_client.domain.policy import SelectionPreferences


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
    token_estimate: int = 100,
    content_size_bytes: int = 256,
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
        content_size_bytes=content_size_bytes,
        token_estimate=token_estimate,
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
        ResolveQueryRequestDto(
            query="python lint",
            interaction_mode="auto",
            prompt_capable=True,
        )
    )

    assert result.status == "selection_required"
    assert [item.slug for item in result.candidates] == ["python.lint", "js.lint"]
    assert result.selection_mode is None
    assert registry_client.metadata_calls == []


def test_query_use_case_returns_interactive_candidate_details_from_core_ranking() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["postman"] = ["postman.old", "postman.new"]
    registry_client.versions_by_slug["postman.old"] = [
        _version_summary(
            "postman.old",
            "1.0.0",
            name="Postman Primary Skill",
            tags=["postman", "primary"],
            token_estimate=200,
            content_size_bytes=79,
            published_at="2026-03-21T22:05:11.334228Z",
        )
    ]
    registry_client.versions_by_slug["postman.new"] = [
        _version_summary(
            "postman.new",
            "1.0.0",
            name="Postman Primary Skill",
            tags=["postman", "primary"],
            token_estimate=200,
            content_size_bytes=79,
            published_at="2026-03-28T16:55:09.761768Z",
        )
    ]

    result = ResolveSkillQueryUseCase(registry_client).execute(
        ResolveQueryRequestDto(
            query="postman",
            interaction_mode="always",
            prompt_capable=True,
        )
    )

    assert result.status == "selection_required"
    assert [item.slug for item in result.candidates] == ["postman.new", "postman.old"]
    assert result.candidates[0].token_estimate == 200
    assert result.candidates[0].content_size_bytes == 79
    assert "tokens=200" in result.candidates[0].selection_details
    assert "size=79B" in result.candidates[0].selection_details
    assert "published=2026-03-28T16:55:09.761768Z" in result.candidates[0].selection_details
    assert result.candidates[0].selection_reason is not None
    assert "newer publication date" in result.candidates[0].selection_reason
    assert result.candidates[1].selection_reason is None



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
        ResolveQueryRequestDto(
            query="python lint",
            interaction_mode="never",
            prompt_capable=False,
        )
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



def test_query_use_case_filters_candidates_by_policy_before_ranking() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["python.lint", "js.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary(
            "python.lint",
            "1.2.3",
            name="Python Lint",
            tags=["python", "lint"],
            trust_tier="internal",
        )
    ]
    registry_client.versions_by_slug["js.lint"] = [
        _version_summary(
            "js.lint",
            "2.1.0",
            name="JavaScript Lint",
            tags=["javascript", "lint"],
            runtime="javascript",
            trust_tier="verified",
        )
    ]
    registry_client.metadata_by_coordinate[("js.lint", "2.1.0")] = _metadata(
        "js.lint",
        "2.1.0",
        name="JavaScript Lint",
        runtime="javascript",
        tags=["javascript", "lint"],
        trust_tier="verified",
    )

    result = ResolveSkillQueryUseCase(
        registry_client,
        policy_context=PolicyContext(allowed_trust_tiers=["verified"]),
    ).execute(ResolveQueryRequestDto(query="lint"))

    assert result.status == "resolved"
    assert [item.slug for item in result.candidates] == ["js.lint"]
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == "js.lint"
    assert result.lockfile is not None
    assert result.lockfile.policy is not None
    assert result.lockfile.policy.allowed_trust_tiers == ["verified"]
    assert any(item.action == "candidate_policy_reject" for item in result.trace)


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


def test_query_use_case_raises_when_policy_rejects_all_candidates() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["python.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary(
            "python.lint",
            "1.2.3",
            name="Python Lint",
            trust_tier="internal",
        )
    ]

    with pytest.raises(PolicyViolationError, match="All discovered candidates were rejected by policy"):
        ResolveSkillQueryUseCase(
            registry_client,
            policy_context=PolicyContext(allowed_trust_tiers=["verified"]),
        ).execute(ResolveQueryRequestDto(query="lint"))


def test_query_use_case_rejects_candidates_by_lifecycle_override() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["archived.lint"]
    registry_client.versions_by_slug["archived.lint"] = [
        _version_summary(
            "archived.lint",
            "1.0.0",
            name="Archived Lint",
            lifecycle_status="archived",
        )
    ]

    with pytest.raises(PolicyViolationError, match="All discovered candidates were rejected by policy"):
        ResolveSkillQueryUseCase(
            registry_client,
            policy_context=PolicyContext(allowed_lifecycle_statuses=["published"]),
        ).execute(ResolveQueryRequestDto(query="lint"))


def test_query_use_case_rejects_candidates_by_content_size_override() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint"] = ["large.lint"]
    registry_client.versions_by_slug["large.lint"] = [
        _version_summary(
            "large.lint",
            "1.0.0",
            name="Large Lint",
            content_size_bytes=4096,
        )
    ]

    with pytest.raises(PolicyViolationError, match="All discovered candidates were rejected by policy"):
        ResolveSkillQueryUseCase(
            registry_client,
            policy_context=PolicyContext(max_content_size_bytes=1024),
        ).execute(ResolveQueryRequestDto(query="lint"))


def test_query_use_case_prefers_low_cost_candidate_under_low_cost_profile() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint tool"] = ["trusted.lint", "cheap.lint"]
    registry_client.versions_by_slug["trusted.lint"] = [
        _version_summary(
            "trusted.lint",
            "1.0.0",
            name="Lint Tool",
            tags=["lint", "tool"],
            trust_tier="verified",
            token_estimate=500,
            content_size_bytes=400,
        )
    ]
    registry_client.versions_by_slug["cheap.lint"] = [
        _version_summary(
            "cheap.lint",
            "1.0.0",
            name="Lint Tool",
            tags=["lint", "tool"],
            trust_tier="internal",
            token_estimate=50,
            content_size_bytes=100,
        )
    ]
    registry_client.metadata_by_coordinate[("cheap.lint", "1.0.0")] = _metadata(
        "cheap.lint",
        "1.0.0",
        name="Lint Tool",
        tags=["lint", "tool"],
        trust_tier="internal",
    )

    result = ResolveSkillQueryUseCase(
        registry_client,
        selection_preferences=SelectionPreferences(profile="low-cost"),
    ).execute(
        ResolveQueryRequestDto(
            query="lint tool",
            interaction_mode="never",
            prompt_capable=False,
        )
    )

    assert result.status == "resolved"
    assert result.selected_coordinate is not None
    assert result.selected_coordinate.slug == "cheap.lint"


def test_query_use_case_raises_when_always_mode_cannot_prompt() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["python lint"] = ["js.lint", "python.lint"]
    registry_client.versions_by_slug["python.lint"] = [
        _version_summary("python.lint", "1.2.3", name="Python Lint", tags=["python", "lint"])
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

    with pytest.raises(InteractiveSelectionUnavailableError):
        ResolveSkillQueryUseCase(registry_client).execute(
            ResolveQueryRequestDto(
                query="python lint",
                interaction_mode="always",
                prompt_capable=False,
            )
        )


def test_query_use_case_emits_selection_explainability_trace_and_lock_metadata() -> None:
    registry_client = FakeRegistryClient()
    registry_client.discovery_by_query["lint tool"] = ["trusted.lint", "cheap.lint"]
    registry_client.versions_by_slug["trusted.lint"] = [
        _version_summary(
            "trusted.lint",
            "1.0.0",
            name="Lint Tool",
            tags=["lint", "tool"],
            trust_tier="verified",
            token_estimate=500,
            content_size_bytes=400,
        )
    ]
    registry_client.versions_by_slug["cheap.lint"] = [
        _version_summary(
            "cheap.lint",
            "1.0.0",
            name="Lint Tool",
            tags=["lint", "tool"],
            trust_tier="internal",
            token_estimate=50,
            content_size_bytes=100,
        )
    ]
    registry_client.metadata_by_coordinate[("cheap.lint", "1.0.0")] = _metadata(
        "cheap.lint",
        "1.0.0",
        name="Lint Tool",
        tags=["lint", "tool"],
        trust_tier="internal",
    )

    result = ResolveSkillQueryUseCase(
        registry_client,
        selection_preferences=SelectionPreferences(
            profile="low-cost",
            interaction_mode="never",
            profile_source="cli_override",
            interaction_mode_source="env_override",
        ),
    ).execute(
        ResolveQueryRequestDto(
            query="lint tool",
            prompt_capable=False,
        )
    )

    assert result.status == "resolved"
    assert result.lockfile is not None
    assert result.lockfile.selection is not None
    assert result.lockfile.selection.profile == "low-cost"
    assert result.lockfile.selection.interaction_mode == "never"
    assert result.lockfile.selection.profile_source == "cli_override"
    assert result.lockfile.selection.interaction_mode_source == "env_override"
    assert any(
        item.action == "apply_selection_preferences"
        and item.data["profile"] == "low-cost"
        and item.data["interaction_mode"] == "never"
        for item in result.trace
    )
    assert any(
        item.action == "explain_final_selection"
        and item.data["selected_slug"] == "cheap.lint"
        and item.data["runner_up_slug"] == "trusted.lint"
        and "lower_token_estimate" in item.data["decisive_signals"]
        for item in result.trace
    )
