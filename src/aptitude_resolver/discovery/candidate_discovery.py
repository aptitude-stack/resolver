"""Discovery-layer orchestration for skill lookup before resolver-owned version choice."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from aptitude_resolver.discovery.intent import parse_search_intent
from aptitude_resolver.discovery.query_builder import build_discovery_query
from aptitude_resolver.domain.errors import (
    DiscoveryNoCandidatesError,
    SkillNotFoundError,
)
from aptitude_resolver.domain.models import (
    DiscoveredSkill,
    DiscoveryQuery,
    SearchIntent,
    SkillIdentity,
    VersionSummary,
)
from aptitude_resolver.domain.tracing import TraceEntry


SLUG_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,127})$")


class RegistryCandidatePort(Protocol):
    """Registry reads required for candidate discovery."""

    def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]: ...

    def fetch_skill_identity(self, slug: str) -> SkillIdentity: ...

    def list_skill_versions(self, slug: str) -> list[VersionSummary]: ...


@dataclass(frozen=True)
class DiscoveryMatchesResult:
    """Discovery output before resolver-owned version selection happens."""

    intent: SearchIntent
    matches: list[DiscoveredSkill] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


class DiscoverSkillCandidatesQuery:
    """Discover skill identities and visible versions for higher-level flows."""

    def __init__(self, registry_client: RegistryCandidatePort) -> None:
        self._registry_client = registry_client

    def execute(
        self,
        query: str,
    ) -> DiscoveryMatchesResult:
        intent = parse_search_intent(query)
        trace = [
            TraceEntry(
                stage="intent",
                action="parse_query",
                message=f"Parsed search intent for query '{query}'.",
                data={
                    "terms": list(intent.terms),
                    "preferred_labels": list(intent.preferred_labels),
                    "language": intent.language,
                    "trust_preference": intent.trust_preference,
                },
            )
        ]

        if self._looks_like_slug(query):
            try:
                identity = self._registry_client.fetch_skill_identity(query)
            except SkillNotFoundError as exc:
                trace.append(
                    TraceEntry(
                        stage="discovery",
                        action="exact_slug_miss",
                        message=f"Slug-like query '{query}' was not found directly; falling back to discovery.",
                    )
                )
                if "." in query:
                    raise SkillNotFoundError(f"Skill not found: {query}") from exc
            else:
                trace.append(
                    TraceEntry(
                        stage="discovery",
                        action="exact_slug_hit",
                        message=f"Slug-like query '{query}' matched skill identity directly.",
                        data={
                            "status": identity.status,
                            "current_version": identity.current_version.version
                            if identity.current_version is not None
                            else None,
                        },
                    )
                )
                match = self._build_discovered_skill(query)
                if match is not None:
                    return DiscoveryMatchesResult(
                        intent=intent,
                        matches=[match],
                        trace=trace,
                    )

        discovery_query = build_discovery_query(intent)
        trace.append(
            TraceEntry(
                stage="query_builder",
                action="build_discovery_query",
                message="Built resolver-owned discovery query.",
                data={
                    "name": discovery_query.name,
                    "description": discovery_query.description,
                    "tags": list(discovery_query.tags),
                },
            )
        )

        slugs = self._registry_client.discover_candidate_slugs(discovery_query)
        trace.append(
            TraceEntry(
                stage="registry",
                action="discover_candidates",
                message="Fetched candidate slugs from the registry.",
                data={"candidate_count": len(slugs), "slugs": list(slugs)},
            )
        )
        if not slugs:
            raise DiscoveryNoCandidatesError(query)

        matches: list[DiscoveredSkill] = []
        for slug in slugs:
            match = self._build_discovered_skill(slug)
            if match is not None:
                matches.append(match)

        if not matches:
            raise DiscoveryNoCandidatesError(query)

        return DiscoveryMatchesResult(intent=intent, matches=matches, trace=trace)

    @staticmethod
    def _looks_like_slug(query: str) -> bool:
        return SLUG_RE.fullmatch(query) is not None and " " not in query

    def _build_discovered_skill(self, slug: str) -> DiscoveredSkill | None:
        versions = self._registry_client.list_skill_versions(slug)
        if not versions:
            return None
        return DiscoveredSkill(
            slug=slug,
            available_versions=list(versions),
        )
