"""Client-owned error types."""

from aptitude_client.domain.errors.client_errors import (
    AptitudeClientError,
    DiscoveryAmbiguousMatchError,
    DiscoveryNoCandidatesError,
    InvalidCoordinateError,
    RegistryAccessError,
    RegistryUnavailableError,
    SkillNotFoundError,
    UnexpectedRegistryResponseError,
    VersionSelectionUnavailableError,
)

__all__ = [
    "AptitudeClientError",
    "DiscoveryAmbiguousMatchError",
    "DiscoveryNoCandidatesError",
    "InvalidCoordinateError",
    "RegistryAccessError",
    "RegistryUnavailableError",
    "SkillNotFoundError",
    "UnexpectedRegistryResponseError",
    "VersionSelectionUnavailableError",
]
