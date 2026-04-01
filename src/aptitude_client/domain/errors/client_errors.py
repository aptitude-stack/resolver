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
    """Raised when an exact skill coordinate or skill slug is not present."""


class SkillSelectionError(AptitudeClientError):
    """Raised when CLI or application-level selection cannot be completed."""


class InvalidCoordinateError(AptitudeClientError):
    """Raised when a supplied slug or version is not valid for the server contract."""


class InvalidLockfileError(AptitudeClientError):
    """Raised when a lockfile payload cannot be parsed or replayed safely."""


class InvalidClientConfigurationError(AptitudeClientError):
    """Raised when client-side configuration cannot be parsed or validated safely."""

    def __init__(self, source: str, details: str) -> None:
        self.source = source
        self.details = details
        super().__init__(f"Invalid client configuration from {source}: {details}")

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["source"] = self.source
        payload["details"] = self.details
        return payload


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

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["query"] = self.query
        return payload


class SelectionSlugNotFoundError(SkillSelectionError):
    """Raised when an explicit slug selection is not present in ranked candidates."""

    def __init__(self, query: str, selected_slug: str, candidates: list[str]) -> None:
        self.query = query
        self.selected_slug = selected_slug
        self.candidates = sorted(candidates)
        super().__init__(
            f"Selected slug '{selected_slug}' was not present in discovery candidates for query: {query}"
        )

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["query"] = self.query
        payload["selected_slug"] = self.selected_slug
        payload["candidates"] = list(self.candidates)
        return payload


class InteractiveSelectionUnavailableError(SkillSelectionError):
    """Raised when prompting is required but the current session cannot prompt."""

    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(
            f"Interactive selection was requested for query '{query}', but prompting is not available in this session."
        )

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["query"] = self.query
        return payload


class DependencyCycleError(AptitudeClientError):
    """Raised when recursive dependency expansion detects a cycle."""

    def __init__(self, cycle_path: list[str]) -> None:
        self.cycle_path = list(cycle_path)
        super().__init__("Dependency cycle detected: " + " -> ".join(self.cycle_path))

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["cycle_path"] = list(self.cycle_path)
        return payload


class VersionConflictError(AptitudeClientError):
    """Raised when the same slug resolves to multiple exact versions."""

    def __init__(self, slug: str, versions: list[str]) -> None:
        self.slug = slug
        self.versions = sorted(set(versions))
        super().__init__(
            f"Version conflict detected for slug '{slug}': {', '.join(self.versions)}"
        )

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["slug"] = self.slug
        payload["versions"] = list(self.versions)
        return payload


class PolicyViolationError(AptitudeClientError):
    """Raised when policy validation rejects a resolved graph."""


class ContentChecksumMismatchError(AptitudeClientError):
    """Raised when downloaded content does not match immutable metadata."""

    def __init__(
        self,
        slug: str,
        version: str,
        algorithm: str,
        expected_digest: str,
        actual_digest: str,
    ) -> None:
        self.slug = slug
        self.version = version
        self.algorithm = algorithm
        self.expected_digest = expected_digest
        self.actual_digest = actual_digest
        super().__init__(
            f"Downloaded content checksum did not match metadata for {slug}@{version}."
        )

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["slug"] = self.slug
        payload["version"] = self.version
        payload["algorithm"] = self.algorithm
        payload["expected_digest"] = self.expected_digest
        payload["actual_digest"] = self.actual_digest
        return payload


class UnsupportedDependencyShapeError(AptitudeClientError):
    """Raised when the current client cannot interpret a dependency selector."""

    def __init__(self, slug: str, version: str, details: str) -> None:
        self.slug = slug
        self.version = version
        self.details = details
        super().__init__(
            f"Unsupported dependency shape for {slug}@{version}: {details}"
        )

    def to_payload(self) -> dict[str, object]:
        payload = super().to_payload()
        payload["slug"] = self.slug
        payload["version"] = self.version
        payload["details"] = self.details
        return payload
