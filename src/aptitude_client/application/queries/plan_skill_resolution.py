"""Shared planning query for discovery, selection, and recursive resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from packaging.version import Version

from aptitude_client.application.dto import ResolveQueryRequestDto
from aptitude_client.discovery import (
    DiscoverSkillCandidatesQuery,
    RegistryCandidatePort,
)
from aptitude_client.discovery.reranking import rerank_candidates
from aptitude_client.domain.errors import (
    DiscoveryNoCandidatesError,
    PolicyViolationError,
)
from aptitude_client.domain.models import DiscoveryCandidate, ResolutionGraph
from aptitude_client.domain.policy import (
    PolicyContext,
    PolicyEvaluation,
    SelectionPreferences,
    lifecycle_status_rank,
    trust_tier_rank,
)
from aptitude_client.domain.tracing import TraceEntry
from aptitude_client.execution import ExecutionPlan, build_execution_plan
from aptitude_client.governance import (
    evaluate_resolution_graph,
    filter_policy_compliant_candidates,
)
from aptitude_client.lockfile import Lockfile, build_lockfile
from aptitude_client.resolver.graph import resolve_recursive_graph
from aptitude_client.resolver.solver import (
    RegistryCandidateVersionPort,
    resolve_candidate_versions,
    select_final_candidate,
)
from aptitude_client.resolver.validation import validate_resolution_graph
from aptitude_client.telemetry import TelemetryCollector, emit_stage_timings


class ResolutionPlanningRegistryPort(
    RegistryCandidatePort, RegistryCandidateVersionPort, Protocol
):
    """Registry operations required for planning one resolved artifact."""

    def fetch_direct_dependencies(self, slug: str, version: str): ...


@dataclass(frozen=True)
class SelectionRequiredResult:
    """Intermediate result indicating that the caller must choose a candidate."""

    requested_query: str
    requested_version: str | None
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ResolutionArtifact:
    """Shared internal planning artifact used by resolve and install flows."""

    requested_query: str
    requested_version: str | None
    selection_mode: str
    candidates: list[DiscoveryCandidate]
    selected_candidate: DiscoveryCandidate
    graph: ResolutionGraph
    lockfile: Lockfile
    execution_plan: ExecutionPlan
    trace: list[TraceEntry] = field(default_factory=list)
    policy_evaluations: list[PolicyEvaluation] = field(default_factory=list)


class PlanSkillResolutionQuery:
    """Plan one selected resolution artifact without binding to a CLI outcome."""

    def __init__(
        self,
        registry_client: ResolutionPlanningRegistryPort,
        *,
        policy_context: PolicyContext | None = None,
        selection_preferences: SelectionPreferences | None = None,
    ) -> None:
        self._registry_client = registry_client
        self._discover_candidates = DiscoverSkillCandidatesQuery(registry_client)
        self._policy_context = policy_context or PolicyContext()
        self._selection_preferences = selection_preferences or SelectionPreferences()

    def execute(
        self,
        request: ResolveQueryRequestDto,
    ) -> SelectionRequiredResult | ResolutionArtifact:
        telemetry = TelemetryCollector()
        try:
            with telemetry.measure("discovery"):
                discovery_result = self._discover_candidates.execute(request.query)
            effective_interaction_mode = (
                request.interaction_mode or self._selection_preferences.interaction_mode
            )
            trace = list(discovery_result.trace)
            with telemetry.measure("resolution"):
                candidates, version_trace = resolve_candidate_versions(
                    discovery_result.intent,
                    discovery_result.matches,
                    self._registry_client,
                    version=request.version,
                )
            trace.extend(version_trace)
            trace.append(
                TraceEntry(
                    stage="selection",
                    action="apply_selection_preferences",
                    message="Applied effective selection preferences for candidate ranking and ambiguity handling.",
                    data={
                        "profile": self._selection_preferences.profile,
                        "interaction_mode": effective_interaction_mode,
                        "profile_source": self._selection_preferences.profile_source,
                        "interaction_mode_source": (
                            "request"
                            if request.interaction_mode is not None
                            else self._selection_preferences.interaction_mode_source
                        ),
                    },
                )
            )
            if not candidates:
                raise DiscoveryNoCandidatesError(request.query)

            with telemetry.measure("governance"):
                candidates, governance_trace = filter_policy_compliant_candidates(
                    candidates,
                    self._policy_context,
                )
            trace.extend(governance_trace)
            if not candidates:
                raise PolicyViolationError(
                    "All discovered candidates were rejected by policy."
                )

            with telemetry.measure("resolution"):
                ranked_candidates = rerank_candidates(
                    discovery_result.intent,
                    candidates,
                    self._selection_preferences,
                )
                selection = select_final_candidate(
                    query=request.query,
                    candidates=ranked_candidates,
                    select_slug=request.select_slug,
                    interaction_mode=effective_interaction_mode,
                    prompt_capable=request.prompt_capable,
                    selection_source=request.selection_source,
                )
            for candidate in ranked_candidates:
                trace.append(
                    TraceEntry(
                        stage="reranking",
                        action="rank_candidate",
                        message=f"Ranked candidate {candidate.slug}@{candidate.selected_coordinate.version}.",
                        data={
                            "ranking_position": candidate.ranking_position,
                            "matched_labels": list(candidate.matched_labels),
                            "match_reasons": list(candidate.match_reasons),
                        },
                    )
                )
            candidates = ranked_candidates
            trace.extend(selection.trace)
            if selection.selected_candidate is None or selection.selection_mode is None:
                return SelectionRequiredResult(
                    requested_query=request.query,
                    requested_version=request.version,
                    candidates=candidates,
                    trace=trace,
                )
            candidate = selection.selected_candidate
            selection_mode = selection.selection_mode

            with telemetry.measure("resolution"):
                graph, resolver_trace = resolve_recursive_graph(
                    candidate.selected_coordinate,
                    self._registry_client,
                )
                validate_resolution_graph(graph)
            trace.extend(resolver_trace)
            with telemetry.measure("governance"):
                policy_evaluations = evaluate_resolution_graph(
                    graph, self._policy_context
                )
            failed_evaluations = [
                item for item in policy_evaluations if not item.passed
            ]
            if failed_evaluations:
                raise PolicyViolationError(failed_evaluations[0].message)

            trace.append(
                TraceEntry(
                    stage="selection",
                    action="finalize_selection",
                    message=f"Selected {candidate.slug}@{candidate.selected_coordinate.version}.",
                    data={"selection_mode": selection_mode},
                )
            )
            selection_explanation = _selection_explanation_trace(
                candidates=candidates,
                selected_candidate=candidate,
                selection_mode=selection_mode,
                selection_preferences=self._selection_preferences,
            )
            if selection_explanation is not None:
                trace.append(selection_explanation)
            with telemetry.measure("lock"):
                lockfile = build_lockfile(
                    graph=graph,
                    requested_query=request.query,
                    requested_version=request.version,
                    selection_mode=selection_mode,
                    policy_evaluations=policy_evaluations,
                    policy_context=self._policy_context,
                    selection_preferences=self._selection_preferences,
                )
            trace.append(
                TraceEntry(
                    stage="lockfile",
                    action="build_lockfile",
                    message=f"Built lockfile for {len(lockfile.nodes)} resolved skills.",
                    data={
                        "node_count": len(lockfile.nodes),
                        "root_node_id": lockfile.root.selected_node_id,
                    },
                )
            )
            with telemetry.measure("execution_planning"):
                execution_plan = build_execution_plan(lockfile)
            trace.append(
                TraceEntry(
                    stage="execution",
                    action="build_execution_plan",
                    message=f"Built execution plan with {len(execution_plan.steps)} steps.",
                    data={
                        "step_count": len(execution_plan.steps),
                        "root_node_id": lockfile.root.selected_node_id,
                    },
                )
            )
            return ResolutionArtifact(
                requested_query=request.query,
                requested_version=request.version,
                selection_mode=selection_mode,
                candidates=candidates,
                selected_candidate=candidate,
                graph=graph,
                lockfile=lockfile,
                execution_plan=execution_plan,
                trace=trace,
                policy_evaluations=policy_evaluations,
            )
        finally:
            emit_stage_timings(telemetry)


def _selection_explanation_trace(
    *,
    candidates: list[DiscoveryCandidate],
    selected_candidate: DiscoveryCandidate,
    selection_mode: str,
    selection_preferences: SelectionPreferences,
) -> TraceEntry | None:
    if len(candidates) < 2:
        return None

    runner_up = next(
        (
            candidate
            for candidate in candidates
            if (
                candidate.slug != selected_candidate.slug
                or candidate.selected_coordinate.version
                != selected_candidate.selected_coordinate.version
            )
        ),
        None,
    )
    if runner_up is None:
        return None

    decisive_signals = _decisive_signals(
        selected_candidate,
        runner_up,
        selection_mode=selection_mode,
        selection_preferences=selection_preferences,
    )
    return TraceEntry(
        stage="selection",
        action="explain_final_selection",
        message=(
            f"Explained why {selected_candidate.slug}@{selected_candidate.selected_coordinate.version} "
            f"won over {runner_up.slug}@{runner_up.selected_coordinate.version}."
        ),
        data={
            "profile": selection_preferences.profile,
            "selection_mode": selection_mode,
            "selected_slug": selected_candidate.slug,
            "selected_version": selected_candidate.selected_coordinate.version,
            "runner_up_slug": runner_up.slug,
            "runner_up_version": runner_up.selected_coordinate.version,
            "decisive_signals": decisive_signals,
        },
    )


def _decisive_signals(
    selected_candidate: DiscoveryCandidate,
    runner_up: DiscoveryCandidate,
    *,
    selection_mode: str,
    selection_preferences: SelectionPreferences,
) -> list[str]:
    if selection_mode == "explicit_slug":
        return ["explicit_slug"]
    if selection_mode == "interactive_choice":
        return ["interactive_choice"]

    selected_version = selected_candidate.selected_version
    runner_version = runner_up.selected_version
    signals: list[str] = list(selected_candidate.match_reasons)

    if _is_lower_known_cost(
        selected_version.token_estimate, runner_version.token_estimate
    ):
        signals.append("lower_token_estimate")
    if _is_lower_known_cost(
        selected_version.content_size_bytes,
        runner_version.content_size_bytes,
    ):
        signals.append("lower_content_size_bytes")
    if trust_tier_rank(selected_version.trust_tier) > trust_tier_rank(
        runner_version.trust_tier
    ):
        signals.append("higher_trust_tier")
    if lifecycle_status_rank(selected_version.lifecycle_status) > lifecycle_status_rank(
        runner_version.lifecycle_status
    ):
        signals.append("better_lifecycle_status")
    if selected_version.is_current_default and not runner_version.is_current_default:
        signals.append("current_default")
    if Version(selected_version.coordinate.version) > Version(
        runner_version.coordinate.version
    ):
        signals.append("newer_semver")

    if not signals:
        signals.append(f"profile_{selection_preferences.profile}")

    return list(dict.fromkeys(signals))


def _is_lower_known_cost(
    selected_value: int | None, runner_up_value: int | None
) -> bool:
    return (
        selected_value is not None
        and runner_up_value is not None
        and selected_value < runner_up_value
    )
