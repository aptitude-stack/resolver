from __future__ import annotations

from aptitude_client.domain.models import (
    DiscoveryCandidate,
    ResolutionGraph,
    ResolvedSkillNode,
    SkillCoordinate,
    VersionSummary,
)
from aptitude_client.domain.policy import PolicyContext
from aptitude_client.governance import (
    evaluate_resolution_graph,
    filter_policy_compliant_candidates,
)


def _version(
    slug: str,
    version: str,
    *,
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
    token_estimate: int | None = 100,
    content_size_bytes: int | None = 256,
) -> VersionSummary:
    return VersionSummary(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=slug,
        description=f"{slug} description",
        tags=["lint"],
        headers={"runtime": "python"},
        rendered_summary=f"{slug} summary",
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
        published_at="2026-03-18T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=content_size_bytes,
        token_estimate=token_estimate,
        maturity_score=0.9,
        security_score=0.95,
    )


def _candidate(
    slug: str,
    version: str,
    *,
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
    token_estimate: int | None = 100,
    content_size_bytes: int | None = 256,
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        slug=slug,
        selected_version=_version(
            slug,
            version,
            lifecycle_status=lifecycle_status,
            trust_tier=trust_tier,
            token_estimate=token_estimate,
            content_size_bytes=content_size_bytes,
        ),
        labels=["lint"],
        matched_labels=["lint"],
        match_reasons=["server_candidate"],
    )


def _node(
    slug: str,
    version: str,
    *,
    lifecycle_status: str = "published",
    trust_tier: str = "internal",
    token_estimate: int | None = 100,
    content_size_bytes: int | None = 256,
) -> ResolvedSkillNode:
    return ResolvedSkillNode(
        coordinate=SkillCoordinate(slug=slug, version=version),
        name=slug,
        description=f"{slug} description",
        tags=["lint"],
        headers={"runtime": "python"},
        rendered_summary=f"{slug} summary",
        lifecycle_status=lifecycle_status,
        trust_tier=trust_tier,
        published_at="2026-03-18T00:00:00Z",
        content_checksum_algorithm="sha256",
        content_checksum_digest=f"digest-{slug}-{version}",
        content_size_bytes=content_size_bytes,
        token_estimate=token_estimate,
        maturity_score=0.9,
        security_score=0.95,
    )


def test_policy_context_phase_1_defaults_are_explicit() -> None:
    context = PolicyContext()

    assert context.profile == "default"
    assert context.source == "client_default"
    assert context.allowed_lifecycle_statuses == ["published", "deprecated", "archived"]
    assert context.allowed_trust_tiers == ["verified", "internal", "untrusted"]
    assert context.max_token_estimate is None
    assert context.max_content_size_bytes is None


def test_filter_policy_compliant_candidates_rejects_illegal_candidates_and_emits_trace() -> None:
    candidates = [
        _candidate("trusted.skill", "1.0.0", trust_tier="verified"),
        _candidate("untrusted.skill", "1.0.0", trust_tier="untrusted"),
    ]

    compliant, trace = filter_policy_compliant_candidates(
        candidates,
        PolicyContext(allowed_trust_tiers=["verified"]),
    )

    assert [candidate.slug for candidate in compliant] == ["trusted.skill"]
    assert [item.action for item in trace] == [
        "candidate_policy_pass",
        "candidate_policy_reject",
        "filter_candidate_policies",
    ]
    assert trace[1].data["failed_rules"] == ["allowed_trust_tiers"]


def test_filter_policy_compliant_candidates_rejects_disallowed_lifecycle() -> None:
    compliant, trace = filter_policy_compliant_candidates(
        [_candidate("archived.skill", "1.0.0", lifecycle_status="archived")],
        PolicyContext(allowed_lifecycle_statuses=["published"]),
    )

    assert compliant == []
    assert trace[0].action == "candidate_policy_reject"
    assert trace[0].data["failed_rules"] == ["allowed_lifecycle_status"]


def test_filter_policy_compliant_candidates_rejects_candidates_above_token_ceiling() -> None:
    compliant, trace = filter_policy_compliant_candidates(
        [_candidate("expensive.skill", "1.0.0", token_estimate=900)],
        PolicyContext(max_token_estimate=500),
    )

    assert compliant == []
    assert trace[0].action == "candidate_policy_reject"
    assert trace[0].data["failed_rules"] == ["max_token_estimate"]


def test_filter_policy_compliant_candidates_fails_closed_for_unknown_resource_values() -> None:
    compliant, trace = filter_policy_compliant_candidates(
        [_candidate("unknown.size", "1.0.0", content_size_bytes=None)],
        PolicyContext(max_content_size_bytes=512),
    )

    assert compliant == []
    assert trace[0].action == "candidate_policy_reject"
    assert trace[0].data["failed_rules"] == ["max_content_size_bytes"]


def test_evaluate_resolution_graph_checks_lifecycle_trust_and_resource_rules() -> None:
    graph = ResolutionGraph(
        root=SkillCoordinate(slug="root.skill", version="1.0.0"),
        nodes=[
            _node("root.skill", "1.0.0", trust_tier="verified", token_estimate=120),
            _node("dep.skill", "1.0.0", lifecycle_status="archived", token_estimate=None),
        ],
        edges=[],
        install_order=[
            SkillCoordinate(slug="root.skill", version="1.0.0"),
            SkillCoordinate(slug="dep.skill", version="1.0.0"),
        ],
        conflicts=[],
    )

    evaluations = evaluate_resolution_graph(
        graph,
        PolicyContext(
            allowed_lifecycle_statuses=["published"],
            allowed_trust_tiers=["verified"],
            max_token_estimate=200,
        ),
    )

    assert any(
        item.rule == "allowed_lifecycle_status" and item.coordinate == SkillCoordinate("dep.skill", "1.0.0") and not item.passed
        for item in evaluations
    )
    assert any(
        item.rule == "max_token_estimate"
        and item.coordinate == SkillCoordinate("dep.skill", "1.0.0")
        and not item.passed
        for item in evaluations
    )


def test_evaluate_resolution_graph_checks_aggregate_resource_ceilings() -> None:
    graph = ResolutionGraph(
        root=SkillCoordinate(slug="root.skill", version="1.0.0"),
        nodes=[
            _node("root.skill", "1.0.0", token_estimate=120, content_size_bytes=300),
            _node("dep.skill", "1.0.0", token_estimate=200, content_size_bytes=400),
        ],
        edges=[],
        install_order=[
            SkillCoordinate(slug="root.skill", version="1.0.0"),
            SkillCoordinate(slug="dep.skill", version="1.0.0"),
        ],
        conflicts=[],
    )

    evaluations = evaluate_resolution_graph(
        graph,
        PolicyContext(
            max_total_token_estimate=250,
            max_total_content_size_bytes=1000,
        ),
    )

    assert any(item.rule == "max_total_token_estimate" and not item.passed for item in evaluations)
    assert any(item.rule == "max_total_content_size_bytes" and item.passed for item in evaluations)
