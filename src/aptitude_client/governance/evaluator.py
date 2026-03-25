"""Policy evaluation seam for resolved graphs."""

from __future__ import annotations

from aptitude_client.domain.policy import PolicyContext, PolicyEvaluation
from aptitude_client.domain.models import ResolutionGraph


def evaluate_resolution_graph(
    graph: ResolutionGraph,
    policy_context: PolicyContext,
) -> list[PolicyEvaluation]:
    """Evaluate resolved nodes against current policy rules."""

    evaluations: list[PolicyEvaluation] = []
    for node in graph.nodes:
        allowed = node.lifecycle_status in policy_context.allowed_lifecycle_statuses
        evaluations.append(
            PolicyEvaluation(
                rule="allowed_lifecycle_status",
                passed=allowed,
                message=(
                    f"Lifecycle '{node.lifecycle_status}' is allowed."
                    if allowed
                    else f"Lifecycle '{node.lifecycle_status}' is not allowed."
                ),
                coordinate=node.coordinate,
            )
        )
    return evaluations
