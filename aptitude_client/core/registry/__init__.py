"""Registry client package."""

from aptitude_client.core.registry.contracts import GetSkillResponse, ListSkillsResponse
from aptitude_client.core.registry.client import RegistryClient
from aptitude_client.core.registry.errors import (
    RegistryClientError,
    RegistryHTTPError,
    RegistryResponseError,
    RegistryTransportError,
)

__all__ = [
    "RegistryClient",
    "ListSkillsResponse",
    "GetSkillResponse",
    "RegistryClientError",
    "RegistryHTTPError",
    "RegistryResponseError",
    "RegistryTransportError",
]
