"""Shared planning query for discovery, selection, and recursive resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

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
from aptitude_client.domain.policy import PolicyContext, PolicyEvaluation
from aptitude_client.domain.tracing import TraceEntry
from aptitude_client.execution import ExecutionPlan, build_execution_plan
from aptitude_client.governance import evaluate_resolution_graph
from aptitude_client.lockfile import Lockfile, build_lockfile
from aptitude_client.resolver.graph import resolve_recursive_graph
from aptitude_client.resolver.solver import (
    RegistryCandidateVersionPort,
    resolve_candidate_versions,
    select_final_candidate,
)
from aptitude_client.resolver.validation import validate_resolution_graph


class ResolutionPlanningRegistryPort(RegistryCandidatePort, RegistryCandidateVersionPort, Protocol):
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
    ) -> None:
        self._registry_client = registry_client
        self._discover_candidates = DiscoverSkillCandidatesQuery(registry_client)
        self._policy_context = policy_context or PolicyContext()

    def execute(
        self,
        request: ResolveQueryRequestDto,
    ) -> SelectionRequiredResult | ResolutionArtifact:
        discovery_result = self._discover_candidates.execute(
            request.query,
        )
        candidates, version_trace = resolve_candidate_versions(
            discovery_result.intent,
            discovery_result.matches,
            self._registry_client,
            version=request.version,
        )
        if not candidates:
            raise DiscoveryNoCandidatesError(request.query)

        ranked_candidates = rerank_candidates(discovery_result.intent, candidates)
        trace = list(discovery_result.trace)
        trace.extend(version_trace)
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
        selection = select_final_candidate(
            query=request.query,
            candidates=candidates,
            select_slug=request.select_slug,
            interactive=request.interactive,
            selection_source=request.selection_source,
        )
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

        graph, resolver_trace = resolve_recursive_graph(
            candidate.selected_coordinate,
            self._registry_client,
        )
        validate_resolution_graph(graph)
        trace.extend(resolver_trace)
        policy_evaluations = evaluate_resolution_graph(graph, self._policy_context)
        failed_evaluations = [item for item in policy_evaluations if not item.passed]
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
        lockfile = build_lockfile(
            graph=graph,
            requested_query=request.query,
            requested_version=request.version,
            selection_mode=selection_mode,
            policy_evaluations=policy_evaluations,
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
