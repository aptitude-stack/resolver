"""Governance helpers for candidate filtering and resolved graph evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aptitude_resolver.domain.models import (
    DiscoveryCandidate,
    ResolutionGraph,
    SkillCoordinate,
)
from aptitude_resolver.domain.policy import PolicyContext, PolicyEvaluation
from aptitude_resolver.domain.tracing import TraceEntry


class PolicySubject(Protocol):
    """Shared policy fields exposed by candidates and resolved nodes."""

    @property
    def coordinate(self) -> SkillCoordinate: ...

    @property
    def lifecycle_status(self) -> str: ...

    @property
    def trust_tier(self) -> str: ...

    @property
    def token_estimate(self) -> int | None: ...

    @property
    def content_size_bytes(self) -> int | None: ...


@dataclass(frozen=True)
class SubjectPolicyDecision:
    """One evaluated subject and the rules that failed for it."""

    evaluations: list[PolicyEvaluation]
    failed_rules: list[str]


def filter_policy_compliant_candidates(
    candidates: list[DiscoveryCandidate],
    policy_context: PolicyContext,
) -> tuple[list[DiscoveryCandidate], list[TraceEntry]]:
    """Filter candidate versions that violate client policy before ranking."""

    compliant: list[DiscoveryCandidate] = []
    trace: list[TraceEntry] = []

    for candidate in candidates:
        decision = _evaluate_subject(candidate.selected_version, policy_context)
        if decision.failed_rules:
            trace.append(
                TraceEntry(
                    stage="governance",
                    action="candidate_policy_reject",
                    message=(
                        f"Rejected candidate {candidate.slug}@"
                        f"{candidate.selected_coordinate.version} by policy."
                    ),
                    data={
                        "slug": candidate.slug,
                        "version": candidate.selected_coordinate.version,
                        "failed_rules": list(decision.failed_rules),
                    },
                )
            )
            continue

        compliant.append(candidate)
        trace.append(
            TraceEntry(
                stage="governance",
                action="candidate_policy_pass",
                message=(
                    f"Candidate {candidate.slug}@{candidate.selected_coordinate.version} "
                    "passed candidate policy."
                ),
                data={
                    "slug": candidate.slug,
                    "version": candidate.selected_coordinate.version,
                    "applied_rules": [
                        evaluation.rule for evaluation in decision.evaluations
                    ],
                },
            )
        )

    trace.append(
        TraceEntry(
            stage="governance",
            action="filter_candidate_policies",
            message=f"Filtered {len(compliant)} of {len(candidates)} discovered candidates by policy.",
            data={
                "input_count": len(candidates),
                "compliant_count": len(compliant),
                "rejected_count": len(candidates) - len(compliant),
            },
        )
    )
    return compliant, trace


def evaluate_resolution_graph(
    graph: ResolutionGraph,
    policy_context: PolicyContext,
) -> list[PolicyEvaluation]:
    """Evaluate resolved nodes against current policy rules."""

    evaluations: list[PolicyEvaluation] = []
    for node in graph.nodes:
        evaluations.extend(_evaluate_subject(node, policy_context).evaluations)
    evaluations.extend(_evaluate_aggregate_token_estimate(graph, policy_context))
    evaluations.extend(_evaluate_aggregate_content_size(graph, policy_context))
    return evaluations


def _evaluate_subject(
    subject: PolicySubject,
    policy_context: PolicyContext,
) -> SubjectPolicyDecision:
    evaluations = [
        _evaluate_lifecycle(subject, policy_context),
        _evaluate_trust(subject, policy_context),
        _evaluate_token_estimate(subject, policy_context),
        _evaluate_content_size(subject, policy_context),
    ]
    failed_rules = [
        evaluation.rule for evaluation in evaluations if not evaluation.passed
    ]
    return SubjectPolicyDecision(evaluations=evaluations, failed_rules=failed_rules)


def _evaluate_lifecycle(
    subject: PolicySubject, policy_context: PolicyContext
) -> PolicyEvaluation:
    allowed = subject.lifecycle_status in policy_context.allowed_lifecycle_statuses
    return PolicyEvaluation(
        rule="allowed_lifecycle_status",
        passed=allowed,
        message=(
            f"Lifecycle '{subject.lifecycle_status}' is allowed."
            if allowed
            else f"Lifecycle '{subject.lifecycle_status}' is not allowed."
        ),
        coordinate=subject.coordinate,
    )


def _evaluate_trust(
    subject: PolicySubject, policy_context: PolicyContext
) -> PolicyEvaluation:
    allowed = subject.trust_tier in policy_context.allowed_trust_tiers
    return PolicyEvaluation(
        rule="allowed_trust_tiers",
        passed=allowed,
        message=(
            f"Trust tier '{subject.trust_tier}' is allowed."
            if allowed
            else f"Trust tier '{subject.trust_tier}' is not allowed."
        ),
        coordinate=subject.coordinate,
    )


def _evaluate_token_estimate(
    subject: PolicySubject,
    policy_context: PolicyContext,
) -> PolicyEvaluation:
    if policy_context.max_token_estimate is None:
        return PolicyEvaluation(
            rule="max_token_estimate",
            passed=True,
            message="No token estimate ceiling is configured.",
            coordinate=subject.coordinate,
        )
    if subject.token_estimate is None:
        return PolicyEvaluation(
            rule="max_token_estimate",
            passed=False,
            message="Token estimate is unknown and fails the configured ceiling.",
            coordinate=subject.coordinate,
        )
    allowed = subject.token_estimate <= policy_context.max_token_estimate
    return PolicyEvaluation(
        rule="max_token_estimate",
        passed=allowed,
        message=(
            f"Token estimate '{subject.token_estimate}' is within policy."
            if allowed
            else f"Token estimate '{subject.token_estimate}' exceeds policy."
        ),
        coordinate=subject.coordinate,
    )


def _evaluate_content_size(
    subject: PolicySubject,
    policy_context: PolicyContext,
) -> PolicyEvaluation:
    if policy_context.max_content_size_bytes is None:
        return PolicyEvaluation(
            rule="max_content_size_bytes",
            passed=True,
            message="No content size ceiling is configured.",
            coordinate=subject.coordinate,
        )
    if subject.content_size_bytes is None:
        return PolicyEvaluation(
            rule="max_content_size_bytes",
            passed=False,
            message="Content size is unknown and fails the configured ceiling.",
            coordinate=subject.coordinate,
        )
    allowed = subject.content_size_bytes <= policy_context.max_content_size_bytes
    return PolicyEvaluation(
        rule="max_content_size_bytes",
        passed=allowed,
        message=(
            f"Content size '{subject.content_size_bytes}' is within policy."
            if allowed
            else f"Content size '{subject.content_size_bytes}' exceeds policy."
        ),
        coordinate=subject.coordinate,
    )


def _evaluate_aggregate_token_estimate(
    graph: ResolutionGraph,
    policy_context: PolicyContext,
) -> list[PolicyEvaluation]:
    if policy_context.max_total_token_estimate is None:
        return [
            PolicyEvaluation(
                rule="max_total_token_estimate",
                passed=True,
                message="No aggregate token estimate ceiling is configured.",
                coordinate=None,
            )
        ]
    if any(node.token_estimate is None for node in graph.nodes):
        return [
            PolicyEvaluation(
                rule="max_total_token_estimate",
                passed=False,
                message="Aggregate token estimate is unknown and fails the configured ceiling.",
                coordinate=None,
            )
        ]
    total = sum(node.token_estimate or 0 for node in graph.nodes)
    allowed = total <= policy_context.max_total_token_estimate
    return [
        PolicyEvaluation(
            rule="max_total_token_estimate",
            passed=allowed,
            message=(
                f"Aggregate token estimate '{total}' is within policy."
                if allowed
                else f"Aggregate token estimate '{total}' exceeds policy."
            ),
            coordinate=None,
        )
    ]


def _evaluate_aggregate_content_size(
    graph: ResolutionGraph,
    policy_context: PolicyContext,
) -> list[PolicyEvaluation]:
    if policy_context.max_total_content_size_bytes is None:
        return [
            PolicyEvaluation(
                rule="max_total_content_size_bytes",
                passed=True,
                message="No aggregate content size ceiling is configured.",
                coordinate=None,
            )
        ]
    if any(node.content_size_bytes is None for node in graph.nodes):
        return [
            PolicyEvaluation(
                rule="max_total_content_size_bytes",
                passed=False,
                message="Aggregate content size is unknown and fails the configured ceiling.",
                coordinate=None,
            )
        ]
    total = sum(node.content_size_bytes or 0 for node in graph.nodes)
    allowed = total <= policy_context.max_total_content_size_bytes
    return [
        PolicyEvaluation(
            rule="max_total_content_size_bytes",
            passed=allowed,
            message=(
                f"Aggregate content size '{total}' is within policy."
                if allowed
                else f"Aggregate content size '{total}' exceeds policy."
            ),
            coordinate=None,
        )
    ]
