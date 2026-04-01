from __future__ import annotations

import pytest

import aptitude.application.queries.plan_skill_resolution as planning_module
from aptitude.application.dto import ResolveQueryRequestDto
from aptitude.application.queries import PlanSkillResolutionQuery
from aptitude.domain.errors import PolicyViolationError, SkillNotFoundError
from aptitude.domain.models import (
    DependencyEdge,
    DependencySpec,
    DiscoveryCandidate,
    DiscoveryQuery,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
    SkillIdentity,
    SkillMetadata,
    VersionSummary,
)
from aptitude.domain.policy import PolicyContext, SelectionPreferences
from aptitude.domain.tracing import TraceEntry


class FakeRegistryClient:
    def __init__(self) -> None:
        self.discovery_by_query: dict[str, list[str]] = {}
        self.identity_by_slug: dict[str, SkillIdentity] = {}
        self.versions_by_slug: dict[str, list[VersionSummary]] = {}
        self.metadata_by_coordinate: dict[tuple[str, str], SkillMetadata] = {}
        self.dependencies_by_coordinate: dict[
            tuple[str, str], list[DependencySpec]
        ] = {}
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
            raise SkillNotFoundError(
                f"Skill version not found: {slug}@{version}"
            ) from exc

    def fetch_direct_dependencies(
        self, slug: str, version: str
    ) -> list[DependencySpec]:
        self.dependency_calls.append((slug, version))
        return list(self.dependencies_by_coordinate.get((slug, version), []))


def _identity(
    slug: str,
    version: str,
    *,
    lifecycle_status: str = "published",
    trust_tier: str = "verified",
) -> SkillIdentity:
    return SkillIdentity(
        slug=slug,
        status="active",
        current_version=SkillCoordinate(slug=slug, version=version),
        current_lifecycle_status=lifecycle_status,
        current_trust_tier=trust_tier,
        current_published_at="2026-03-18T00:00:00Z",
        created_at="2026-03-01T00:00:00Z",
        updated_at="2026-03-18T00:00:00Z",
    )


def _version(
    slug: str,
    version: str,
    *,
    name: str = "Python Lint",
    description: str = "Lint Python files",
    tags: list[str] | None = None,
    runtime: str = "python",
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
    token_estimate: int | None = 100,
    content_size_bytes: int | None = 256,
    published_at: str = "2026-03-18T00:00:00Z",
    is_current_default: bool = False,
) -> VersionSummary:
    return VersionSummary(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=description,
        tags=list(tags or ["python", "lint"]),
        headers={"runtime": runtime} if runtime else {},
        rendered_summary=f"{name} summary" if name else "",
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
        published_at=published_at,
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=content_size_bytes,
        token_estimate=token_estimate,
        maturity_score=0.9,
        security_score=0.95,
        is_current_default=is_current_default,
    )


def _metadata(
    slug: str,
    version: str,
    *,
    name: str,
    description: str | None = None,
    runtime: str = "python",
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
    token_estimate: int | None = 100,
    content_size_bytes: int | None = 256,
) -> SkillMetadata:
    return SkillMetadata(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=name,
        description=description or f"{name} description",
        tags=["python", "lint"],
        headers={"runtime": runtime},
        inputs_schema={"type": "object"},
        outputs_schema={"type": "object"},
        token_estimate=token_estimate,
        maturity_score=0.9,
        security_score=0.95,
        rendered_summary=f"{name} summary",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=content_size_bytes,
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
        published_at="2026-03-18T00:00:00Z",
    )


def _candidate(
    slug: str,
    version: str,
    *,
    match_reasons: list[str] | None = None,
    token_estimate: int | None = 100,
    content_size_bytes: int | None = 256,
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
    is_current_default: bool = False,
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        slug=slug,
        selected_version=_version(
            slug,
            version,
            token_estimate=token_estimate,
            content_size_bytes=content_size_bytes,
            lifecycle_status=lifecycle_status,
            trust_tier=trust_tier,
            is_current_default=is_current_default,
        ),
        labels=["python", "lint"],
        matched_labels=["python"],
        match_reasons=list(match_reasons or []),
    )


def _node(
    slug: str,
    version: str,
    *,
    name: str,
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
) -> ResolvedSkillNode:
    metadata = _metadata(
        slug,
        version,
        name=name,
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
    )
    return ResolvedSkillNode(
        coordinate=metadata.coordinate,
        name=metadata.name,
        description=metadata.description,
        tags=list(metadata.tags),
        headers=dict(metadata.headers),
        rendered_summary=metadata.rendered_summary,
        lifecycle_status=metadata.lifecycle_status,
        trust_tier=metadata.trust_tier,
        published_at=metadata.published_at,
        content_checksum_algorithm=metadata.content_checksum_algorithm,
        content_checksum_digest=metadata.content_checksum_digest,
        content_size_bytes=metadata.content_size_bytes,
        token_estimate=metadata.token_estimate,
        maturity_score=metadata.maturity_score,
        security_score=metadata.security_score,
    )


@pytest.mark.parametrize(
    ("selection_mode", "expected_signal"),
    [
        ("explicit_slug", "explicit_slug"),
        ("interactive_choice", "interactive_choice"),
    ],
)
def test_selection_explanation_trace_marks_user_driven_selection_modes(
    selection_mode: str, expected_signal: str
) -> None:
    selected = _candidate("python.lint", "2.0.0")
    runner_up = _candidate("js.lint", "1.0.0")

    trace = planning_module._selection_explanation_trace(
        candidates=[selected, runner_up],
        selected_candidate=selected,
        selection_mode=selection_mode,
        selection_preferences=SelectionPreferences(),
    )

    assert trace is not None
    assert trace.data["selection_mode"] == selection_mode
    assert trace.data["decisive_signals"] == [expected_signal]


def test_decisive_signals_add_only_supported_rank_deltas() -> None:
    selected = _candidate(
        "python.lint",
        "2.0.0",
        match_reasons=["exact_name_match"],
        token_estimate=100,
        content_size_bytes=128,
        lifecycle_status="published",
        trust_tier="internal",
        is_current_default=True,
    )
    runner_up = _candidate(
        "js.lint",
        "1.0.0",
        token_estimate=200,
        content_size_bytes=512,
        lifecycle_status="deprecated",
        trust_tier="untrusted",
    )

    signals = planning_module._decisive_signals(
        selected,
        runner_up,
        selection_mode="non_interactive_top_ranked",
        selection_preferences=SelectionPreferences(),
    )

    assert signals == [
        "exact_name_match",
        "lower_token_estimate",
        "lower_content_size_bytes",
        "higher_trust_tier",
        "better_lifecycle_status",
        "current_default",
        "newer_semver",
    ]


def test_decisive_signals_fall_back_to_profile_when_no_decisive_delta_exists() -> None:
    selected = _candidate(
        "python.lint",
        "1.0.0",
        match_reasons=[],
        token_estimate=200,
        content_size_bytes=512,
        trust_tier="internal",
        lifecycle_status="published",
    )
    runner_up = _candidate(
        "js.lint",
        "1.0.0",
        match_reasons=[],
        token_estimate=200,
        content_size_bytes=512,
        trust_tier="internal",
        lifecycle_status="published",
    )

    signals = planning_module._decisive_signals(
        selected,
        runner_up,
        selection_mode="non_interactive_top_ranked",
        selection_preferences=SelectionPreferences(profile="balanced"),
    )

    assert signals == ["profile_balanced"]


def test_execute_raises_policy_violation_for_resolved_dependency_graph() -> None:
    registry_client = FakeRegistryClient()
    registry_client.identity_by_slug["verified.root"] = _identity(
        "verified.root",
        "1.2.3",
        trust_tier="verified",
    )
    registry_client.versions_by_slug["verified.root"] = [
        _version(
            "verified.root",
            "1.2.3",
            name="Verified Root",
            trust_tier="verified",
        )
    ]
    registry_client.metadata_by_coordinate[("verified.root", "1.2.3")] = _metadata(
        "verified.root",
        "1.2.3",
        name="Verified Root",
        trust_tier="verified",
    )
    registry_client.metadata_by_coordinate[("internal.dep", "1.0.0")] = _metadata(
        "internal.dep",
        "1.0.0",
        name="Internal Dependency",
        trust_tier="internal",
    )
    registry_client.dependencies_by_coordinate[("verified.root", "1.2.3")] = [
        DependencySpec(slug="internal.dep", version="1.0.0")
    ]

    query = PlanSkillResolutionQuery(
        registry_client,
        policy_context=PolicyContext(allowed_trust_tiers=["verified"]),
    )

    with pytest.raises(
        PolicyViolationError, match="Trust tier 'internal' is not allowed."
    ):
        query.execute(ResolveQueryRequestDto(query="verified.root"))

    assert registry_client.metadata_calls == [
        ("verified.root", "1.2.3"),
        ("internal.dep", "1.0.0"),
    ]
    assert registry_client.dependency_calls == [
        ("verified.root", "1.2.3"),
        ("internal.dep", "1.0.0"),
    ]


def test_execute_validates_graph_before_lock_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_client = FakeRegistryClient()
    registry_client.identity_by_slug["python.lint"] = _identity("python.lint", "1.2.3")
    registry_client.versions_by_slug["python.lint"] = [
        _version("python.lint", "1.2.3", name="Python Lint")
    ]

    invalid_graph = ResolutionGraph(
        root=SkillCoordinate(slug="python.lint", version="1.2.3"),
        nodes=[_node("python.lint", "1.2.3", name="Python Lint")],
        edges=[
            DependencyEdge(
                source=SkillCoordinate(slug="missing.dep", version="9.9.9"),
                target=SkillCoordinate(slug="python.lint", version="1.2.3"),
            )
        ],
        install_order=[SkillCoordinate(slug="python.lint", version="1.2.3")],
    )

    monkeypatch.setattr(
        planning_module,
        "resolve_recursive_graph",
        lambda root, client: (
            invalid_graph,
            [
                TraceEntry(
                    stage="resolver", action="visit_node", message="invalid", data={}
                )
            ],
        ),
    )

    def _fail_build_lockfile(**_: object) -> None:
        pytest.fail("build_lockfile should not run when graph validation fails")

    monkeypatch.setattr(planning_module, "build_lockfile", _fail_build_lockfile)

    query = PlanSkillResolutionQuery(registry_client)

    with pytest.raises(
        ValueError, match="Resolution graph edge source was not present in nodes."
    ):
        query.execute(ResolveQueryRequestDto(query="python.lint"))
