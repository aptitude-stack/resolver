"""Domain models package."""

from aptitude_resolver.domain.models.dependency_spec import DependencySpec
from aptitude_resolver.domain.models.discovered_skill import DiscoveredSkill
from aptitude_resolver.domain.models.discovery_candidate import DiscoveryCandidate
from aptitude_resolver.domain.models.discovery_query import DiscoveryQuery
from aptitude_resolver.domain.models.resolution_graph import (
    ConflictRecord,
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
)
from aptitude_resolver.domain.models.search_intent import SearchIntent
from aptitude_resolver.domain.models.skill_coordinate import SkillCoordinate
from aptitude_resolver.domain.models.skill_identity import SkillIdentity
from aptitude_resolver.domain.models.skill_metadata import SkillMetadata
from aptitude_resolver.domain.models.version_summary import VersionSummary

__all__ = [
    "ConflictRecord",
    "DependencyEdge",
    "DependencySpec",
    "DiscoveredSkill",
    "DiscoveryCandidate",
    "DiscoveryQuery",
    "ResolutionGraph",
    "ResolvedSkillNode",
    "SearchIntent",
    "SkillCoordinate",
    "SkillIdentity",
    "SkillMetadata",
    "VersionSummary",
]
