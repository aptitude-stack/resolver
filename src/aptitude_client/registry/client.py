"""Sync registry read adapter for the Aptitude client."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from aptitude_client.domain.errors import (
    InvalidCoordinateError,
    RegistryAccessError,
    RegistryUnavailableError,
    SkillNotFoundError,
    UnexpectedRegistryResponseError,
)
from aptitude_client.domain.models import DependencySpec, SkillMetadata
from aptitude_client.registry.mappers import map_direct_dependencies, map_metadata_response
from aptitude_client.registry.transport_models import (
    DiscoveryResponse,
    DirectDependenciesResponse,
    ErrorEnvelope,
    MetadataResponse,
)
from aptitude_client.shared.config import Settings


class RegistryClient:
    """Read-only adapter over the runtime-tested registry contract."""

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client()
        self._owns_http_client = http_client is None

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        """Fetch exact immutable metadata for one skill coordinate."""

        payload = self._get_json(f"/skills/{slug}/versions/{version}")

        try:
            response_model = MetadataResponse.model_validate(payload)
        except ValidationError as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned malformed metadata payload."
            ) from exc

        return map_metadata_response(response_model)

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]:
        """Fetch direct dependency declarations for one skill coordinate."""

        payload = self._get_json(f"/resolution/{slug}/{version}")

        try:
            response_model = DirectDependenciesResponse.model_validate(payload)
        except ValidationError as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned malformed dependency payload."
            ) from exc

        return map_direct_dependencies(response_model)

    def discover_candidates(self, query: str) -> list[str]:
        """Discover candidate slugs for a user query."""

        payload = self._post_json("/discovery", {"name": query})

        try:
            response_model = DiscoveryResponse.model_validate(payload)
        except ValidationError as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned malformed discovery payload."
            ) from exc

        return list(response_model.candidates)

    def close(self) -> None:
        """Close the owned HTTP client."""

        if self._owns_http_client:
            self._http_client.close()

    def _get_json(self, path: str) -> dict[str, Any]:
        return self._request_json("GET", path)

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", path, body)

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._http_client.request(
                method,
                f"{self._settings.server_base_url}{path}",
                headers={"Authorization": f"Bearer {self._settings.read_token}"},
                timeout=self._settings.server_timeout_seconds,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise RegistryUnavailableError("Registry is unavailable.") from exc

        if response.status_code >= 400:
            self._raise_for_error_response(response)

        try:
            payload = response.json()
        except ValueError as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned a non-JSON response."
            ) from exc

        if not isinstance(payload, dict):
            raise UnexpectedRegistryResponseError(
                "Registry returned an unexpected response shape."
            )

        return payload

    def _raise_for_error_response(self, response: httpx.Response) -> None:
        try:
            envelope = ErrorEnvelope.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned a malformed error response."
            ) from exc

        code = envelope.error.code
        message = envelope.error.message

        if response.status_code == 404 and code == "SKILL_VERSION_NOT_FOUND":
            raise SkillNotFoundError(message)

        if response.status_code == 422 and code == "INVALID_REQUEST":
            raise InvalidCoordinateError(message)

        if response.status_code in {401, 403}:
            raise RegistryAccessError(message)

        raise UnexpectedRegistryResponseError(message)
