"""Client-owned error types."""

from aptitude_client.domain.errors.client_errors import (
    AptitudeClientError,
    ContentChecksumMismatchError,
    DependencyCycleError,
    DiscoveryNoCandidatesError,
    InvalidCoordinateError,
    InvalidLockfileError,
    PolicyViolationError,
    RegistryAccessError,
    RegistryUnavailableError,
    SelectionSlugNotFoundError,
    SkillNotFoundError,
    SkillSelectionError,
    UnsupportedDependencyShapeError,
    UnexpectedRegistryResponseError,
    VersionConflictError,
)

__all__ = [
    "AptitudeClientError",
    "ContentChecksumMismatchError",
    "DependencyCycleError",
    "DiscoveryNoCandidatesError",
    "InvalidCoordinateError",
    "InvalidLockfileError",
    "PolicyViolationError",
    "RegistryAccessError",
    "RegistryUnavailableError",
    "SelectionSlugNotFoundError",
    "SkillNotFoundError",
    "SkillSelectionError",
    "UnsupportedDependencyShapeError",
    "UnexpectedRegistryResponseError",
    "VersionConflictError",
]
