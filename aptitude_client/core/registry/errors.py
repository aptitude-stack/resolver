"""Structured errors raised by the registry client."""

from typing import Any, Optional


class RegistryClientError(Exception):
    """Base error for all registry client failures."""


class RegistryTransportError(RegistryClientError):
    """Raised when the HTTP request cannot be completed."""


class RegistryHTTPError(RegistryClientError):
    """Raised when the registry responds with an error status code."""

    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Any] = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.__str__())

    def __str__(self) -> str:
        code = f" [{self.error_code}]" if self.error_code else ""
        return f"Registry HTTP {self.status_code}{code}: {self.message}"


class RegistryResponseError(RegistryClientError):
    """Raised when the response payload is not valid for expected contracts."""
