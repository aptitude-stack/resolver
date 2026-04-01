"""Domain models package."""

from aptitude.domain.models.dependency_spec import DependencySpec
from aptitude.domain.models.discovered_skill import DiscoveredSkill
from aptitude.domain.models.discovery_candidate import DiscoveryCandidate
from aptitude.domain.models.discovery_query import DiscoveryQuery
from aptitude.domain.models.resolution_graph import (
    ConflictRecord,
    DependencyEdge,
    ResolutionGraph,
    ResolvedSkillNode,
)
from aptitude.domain.models.search_intent import SearchIntent
from aptitude.domain.models.skill_coordinate import SkillCoordinate
from aptitude.domain.models.skill_identity import SkillIdentity
from aptitude.domain.models.skill_metadata import SkillMetadata
from aptitude.domain.models.version_summary import VersionSummary

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
