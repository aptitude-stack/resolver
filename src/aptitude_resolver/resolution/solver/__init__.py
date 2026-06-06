"""Resolver solver package."""

from aptitude_resolver.resolution.solver.candidate_version_resolution import (
    RegistryCandidateVersionPort,
    resolve_candidate_versions,
)
from aptitude_resolver.resolution.solver.candidate_selection import (
    FinalCandidateSelection,
    limit_candidates_for_prompt,
    select_final_candidate,
)
from aptitude_resolver.resolution.solver.version_selection import (
    select_preferred_version,
)

__all__ = [
    "FinalCandidateSelection",
    "RegistryCandidateVersionPort",
    "limit_candidates_for_prompt",
    "select_final_candidate",
    "resolve_candidate_versions",
    "select_preferred_version",
]
