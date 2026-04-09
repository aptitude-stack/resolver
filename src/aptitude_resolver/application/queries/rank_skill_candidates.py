"""Shared query for discovery, version enrichment, governance filtering, and reranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from aptitude_resolver.discovery import (
    DiscoverSkillCandidatesQuery,
    RegistryCandidatePort,
)
from aptitude_resolver.discovery.reranking import rerank_candidates
from aptitude_resolver.domain.errors import DiscoveryNoCandidatesError, PolicyViolationError
from aptitude_resolver.domain.models import DiscoveryCandidate, SearchIntent
from aptitude_resolver.domain.policy import PolicyContext, PolicyEvaluation, SelectionPreferences
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.governance import filter_policy_compliant_candidates
from aptitude_resolver.resolution.solver import (
    RegistryCandidateVersionPort,
    resolve_candidate_versions,
)
from aptitude_resolver.telemetry import TelemetryCollector, emit_stage_timings


class RankedCandidatesRegistryPort(RegistryCandidatePort, RegistryCandidateVersionPort, Protocol):
    """Registry operations required for candidate ranking before final selection."""


@dataclass(frozen=True)
class RankedCandidatesArtifact:
    """Discovery candidates after resolver-owned version choice and reranking."""

    requested_query: str
    requested_version: str | None
    intent: SearchIntent
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)
    policy_evaluations: list[PolicyEvaluation] = field(default_factory=list)


class RankSkillCandidatesQuery:
    """Rank legal discovery candidates without resolving a dependency graph."""

    def __init__(
        self,
        registry_client: RankedCandidatesRegistryPort,
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
        *,
        query: str,
        version: str | None = None,
        interaction_mode: str | None = None,
    ) -> RankedCandidatesArtifact:
        telemetry = TelemetryCollector()
        try:
            with telemetry.measure("discovery"):
                discovery_result = self._discover_candidates.execute(query)
            trace = list(discovery_result.trace)
            effective_interaction_mode = (
                interaction_mode or self._selection_preferences.interaction_mode
            )
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
                            if interaction_mode is not None
                            else self._selection_preferences.interaction_mode_source
                        ),
                    },
                )
            )
            with telemetry.measure("resolution"):
                candidates, version_trace = resolve_candidate_versions(
                    discovery_result.intent,
                    discovery_result.matches,
                    self._registry_client,
                    version=version,
                )
            trace.extend(version_trace)
            if not candidates:
                raise DiscoveryNoCandidatesError(query)

            with telemetry.measure("governance"):
                candidates, governance_trace = filter_policy_compliant_candidates(
                    candidates,
                    self._policy_context,
                )
            trace.extend(governance_trace)
            if not candidates:
                raise PolicyViolationError("All discovered candidates were rejected by policy.")

            candidates = rerank_candidates(
                discovery_result.intent,
                candidates,
                self._selection_preferences,
            )
            for candidate in candidates:
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

            return RankedCandidatesArtifact(
                requested_query=query,
                requested_version=version,
                intent=discovery_result.intent,
                candidates=candidates,
                trace=trace,
                policy_evaluations=[],
            )
        finally:
            emit_stage_timings(telemetry)
