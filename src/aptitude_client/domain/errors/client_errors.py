"""Client-owned error types used across Aptitude client layers."""

from __future__ import annotations


class AptitudeClientError(Exception):
    """Base error for client-controlled failures."""

    def to_payload(self) -> dict[str, object]:
        """Return a structured payload suitable for CLI error output."""

        return {
            "type": self.__class__.__name__,
            "message": str(self),
        }


class SkillNotFoundError(AptitudeClientError):
    """Raised when an exact skill coordinate is not present in the registry."""


class InvalidCoordinateError(AptitudeClientError):
    """Raised when a supplied slug or version is not valid for the server contract."""


class RegistryUnavailableError(AptitudeClientError):
    """Raised when the registry cannot be reached."""


class RegistryAccessError(AptitudeClientError):
    """Raised when registry access is denied or unauthorized."""


class UnexpectedRegistryResponseError(AptitudeClientError):
    """Raised when the registry returns an unexpected response shape."""


class DiscoveryNoCandidatesError(AptitudeClientError):
    """Raised when discovery returns no candidates for a user query."""

    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(f"Discovery returned no candidates for query: {query}")


class DiscoveryAmbiguousMatchError(AptitudeClientError):
    """Raised when discovery returns multiple candidates and none is exact."""

    def __init__(self, query: str, candidates: list[str]) -> None:
        self.query = query
        self.candidates = sorted(candidates)
        super().__init__(f"Discovery returned multiple candidates for query: {query}")

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["query"] = self.query
        payload["candidates"] = list(self.candidates)
        return payload


class VersionSelectionUnavailableError(AptitudeClientError):
    """Raised when discovery cannot derive a concrete version from the server."""

    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(
            "Discovery currently requires --version because the server does not expose version lookup routes."
        )

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["query"] = self.query
        return payload
