"""Application query package."""

from aptitude_resolver.application.queries.plan_skill_resolution import (
    PlanSkillResolutionQuery,
    ResolutionArtifact,
    SelectionRequiredResult,
)
from aptitude_resolver.application.queries.rank_skill_candidates import (
    RankSkillCandidatesQuery,
    RankedCandidatesArtifact,
)

__all__ = [
    "PlanSkillResolutionQuery",
    "RankSkillCandidatesQuery",
    "RankedCandidatesArtifact",
    "ResolutionArtifact",
    "SelectionRequiredResult",
]
