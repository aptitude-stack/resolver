"""Discovery-layer orchestration for skill lookup before resolver-owned version choice."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from semver import Version

from aptitude_resolver.discovery.intent import parse_search_intent
from aptitude_resolver.discovery.query_builder import build_discovery_query
from aptitude_resolver.domain.errors import (
    DiscoveryNoCandidatesError,
    InvalidLockfileError,
    SkillNotFoundError,
)
from aptitude_resolver.domain.models import (
    DiscoveredSkill,
    DiscoveryQuery,
    SearchIntent,
    SkillCoordinate,
    SkillIdentity,
    VersionSummary,
)
from aptitude_resolver.domain.tracing import TraceEntry
from aptitude_resolver.lockfile import load_lockfile
from aptitude_resolver.shared.config import default_aptitude_state_dir


SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,127})$")
DISCOVERY_CONTEXT_LIMIT = 50


def load_discovery_context(*, cwd: Path | None = None) -> list[SkillCoordinate]:
    """Load project and global lock coordinates for discovery context."""

    project_path = (cwd or Path.cwd()) / "aptitude.lock.json"
    global_path = default_aptitude_state_dir() / "aptitude.lock.json"
    coordinates: list[SkillCoordinate] = []
    seen_slugs: set[str] = set()

    for path in (project_path, global_path):
        try:
            lockfile = load_lockfile(path)
        except (OSError, InvalidLockfileError, UnicodeDecodeError):
            continue
        for node in lockfile.nodes:
            if SLUG_RE.fullmatch(node.slug) is None:
                continue
            try:
                Version.parse(node.version)
            except ValueError:
                continue
            if node.slug in seen_slugs:
                continue
            seen_slugs.add(node.slug)
            coordinates.append(SkillCoordinate(slug=node.slug, version=node.version))
            if len(coordinates) == DISCOVERY_CONTEXT_LIMIT:
                return coordinates
    return coordinates


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

    def __init__(
        self,
        registry_client: RegistryCandidatePort,
        *,
        cwd: Path | None = None,
    ) -> None:
        self._registry_client = registry_client
        self._cwd = cwd

    def execute(
        self,
        query: str,
        *,
        exact: bool = False,
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

        if exact:
            try:
                identity = self._registry_client.fetch_skill_identity(query)
            except SkillNotFoundError as exc:
                raise SkillNotFoundError(f"Skill not found: {query}") from exc
            if identity.current_version is None:
                raise SkillNotFoundError(f"Skill not found: {query}")
            match = self._build_discovered_skill(query)
            if match is None:
                raise SkillNotFoundError(f"Skill not found: {query}")
            trace.append(
                TraceEntry(
                    stage="discovery",
                    action="exact_slug_hit",
                    message=f"Exact skill slug '{query}' matched skill identity directly.",
                    data={
                        "status": identity.status,
                        "current_version": identity.current_version.version,
                    },
                )
            )
            return DiscoveryMatchesResult(intent=intent, matches=[match], trace=trace)

        context_skills = load_discovery_context(cwd=self._cwd)
        discovery_query = build_discovery_query(
            intent,
            context_skills=context_skills,
        )
        trace.append(
            TraceEntry(
                stage="query_builder",
                action="build_discovery_query",
                message="Built resolver-owned discovery query.",
                data={
                    "query": discovery_query.query,
                    "tags": list(discovery_query.tags),
                    "context_skills": [
                        {"slug": coordinate.slug, "version": coordinate.version}
                        for coordinate in discovery_query.context_skills
                    ],
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

    def _build_discovered_skill(self, slug: str) -> DiscoveredSkill | None:
        versions = self._registry_client.list_skill_versions(slug)
        if not versions:
            return None
        return DiscoveredSkill(
            slug=slug,
            available_versions=list(versions),
        )
