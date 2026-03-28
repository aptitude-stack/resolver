"""Sync registry read adapter for the Aptitude client."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from aptitude_client.cache import (
    CacheStore,
    content_key,
    coordinate_content_key,
    discovery_key,
    metadata_key,
    version_list_key,
)
from aptitude_client.domain.errors import (
    InvalidCoordinateError,
    RegistryAccessError,
    RegistryUnavailableError,
    SkillNotFoundError,
    UnexpectedRegistryResponseError,
)
from aptitude_client.domain.models import (
    DependencySpec,
    DiscoveryQuery,
    SkillIdentity,
    SkillMetadata,
    VersionSummary,
)
from aptitude_client.registry.mappers import (
    map_direct_dependencies,
    map_metadata_response,
    map_skill_version_list_response,
)
from aptitude_client.registry.transport_models import (
    DiscoveryResponse,
    DirectDependenciesResponse,
    ErrorEnvelope,
    MetadataResponse,
    SkillVersionListResponse,
)
from aptitude_client.shared.config import Settings


DISCOVERY_CACHE_TTL_SECONDS = 60
METADATA_CACHE_TTL_SECONDS = 3600
VERSION_LIST_CACHE_TTL_SECONDS = 3600
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class _TransientRegistryError(Exception):
    """Internal retry signal for transient transport or server failures."""

    def __init__(self, response: httpx.Response | None = None) -> None:
        self.response = response
        super().__init__("Transient registry failure")


class RegistryClient:
    """Read-only adapter over the runtime-tested registry contract."""

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.Client | None = None,
        cache_store: CacheStore | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.Client()
        self._owns_http_client = http_client is None
        self._cache_store = cache_store or CacheStore()
        self._owns_cache_store = cache_store is None

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        """Fetch exact immutable metadata for one skill coordinate."""

        payload = self._get_json_with_cache(
            metadata_key(slug, version),
            f"/skills/{slug}/{version}",
            expire=METADATA_CACHE_TTL_SECONDS,
        )
        try:
            response_model = MetadataResponse.model_validate(payload)
        except ValidationError as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned malformed metadata payload."
            ) from exc
        return map_metadata_response(response_model)

    def list_skill_versions(self, slug: str) -> list[VersionSummary]:
        """List immutable versions for one skill identity."""

        payload = self._get_json_with_cache(
            version_list_key(slug),
            f"/skills/{slug}",
            expire=VERSION_LIST_CACHE_TTL_SECONDS,
        )
        try:
            response_model = SkillVersionListResponse.model_validate(payload)
        except ValidationError as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned malformed version list payload."
            ) from exc
        return map_skill_version_list_response(response_model)

    def fetch_skill_identity(self, slug: str) -> SkillIdentity:
        """Synthesize logical skill identity metadata from the live version-list endpoint."""

        versions = self.list_skill_versions(slug)
        current_version = next(
            (item for item in versions if item.is_current_default),
            versions[0] if versions else None,
        )
        return SkillIdentity(
            slug=slug,
            status="active",
            current_version=current_version.coordinate if current_version is not None else None,
            current_lifecycle_status=(
                current_version.lifecycle_status if current_version is not None else None
            ),
            current_trust_tier=current_version.trust_tier if current_version is not None else None,
            current_published_at=current_version.published_at if current_version is not None else None,
            created_at=None,
            updated_at=None,
        )

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

    def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]:
        """Discover candidate slugs for a client-owned discovery query."""

        body: dict[str, Any] = {"name": query.name}
        if query.description:
            body["description"] = query.description
        if query.tags:
            body["tags"] = list(query.tags)

        payload = self._post_json_with_cache(
            discovery_key(query),
            "/discovery",
            body,
            expire=DISCOVERY_CACHE_TTL_SECONDS,
        )
        try:
            response_model = DiscoveryResponse.model_validate(payload)
        except ValidationError as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned malformed discovery payload."
            ) from exc
        return list(response_model.candidates)

    def discover_candidates(self, query: str) -> list[str]:
        """Backward-compatible discovery helper for the earlier exact slice."""

        return self.discover_candidate_slugs(DiscoveryQuery(name=query))

    def fetch_skill_content(
        self,
        slug: str,
        version: str,
        *,
        checksum_algorithm: str | None = None,
        checksum_digest: str | None = None,
    ) -> str:
        """Fetch canonical immutable markdown content for one exact coordinate."""

        cache_key = (
            content_key(algorithm=checksum_algorithm, digest=checksum_digest)
            if checksum_algorithm is not None and checksum_digest is not None
            else coordinate_content_key(slug, version)
        )
        cached = self._cache_store.get(cache_key)
        if isinstance(cached, str):
            return cached

        content = self._get_text(f"/skills/{slug}/{version}/content")
        self._cache_store.set(cache_key, content, expire=None)
        return content

    def close(self) -> None:
        """Close the owned HTTP client."""

        if self._owns_http_client:
            self._http_client.close()
        if self._owns_cache_store:
            self._cache_store.close()

    def _get_json(self, path: str) -> dict[str, Any]:
        return self._request_json("GET", path)

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", path, body)

    def _get_json_with_cache(
        self,
        cache_key: str,
        path: str,
        *,
        expire: int | None,
    ) -> dict[str, Any]:
        cached = self._cache_store.get(cache_key)
        if isinstance(cached, dict):
            return dict(cached)

        payload = self._get_json(path)
        self._cache_store.set(cache_key, payload, expire=expire)
        return payload

    def _post_json_with_cache(
        self,
        cache_key: str,
        path: str,
        body: dict[str, Any],
        *,
        expire: int | None,
    ) -> dict[str, Any]:
        cached = self._cache_store.get(cache_key)
        if isinstance(cached, dict):
            return dict(cached)

        payload = self._post_json(path, body)
        self._cache_store.set(cache_key, payload, expire=expire)
        return payload

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request(method, path, body)

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

    def _get_text(self, path: str) -> str:
        response = self._request("GET", path)
        return response.text

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
                retry=retry_if_exception_type(_TransientRegistryError),
                reraise=True,
            ):
                with attempt:
                    response = self._request_once(method, path, body)
        except _TransientRegistryError as exc:
            raise RegistryUnavailableError("Registry is unavailable.") from exc

        if response.status_code >= 400:
            self._raise_for_error_response(response)
        return response

    def _request_once(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            response = self._http_client.request(
                method,
                f"{self._settings.server_base_url}{path}",
                headers={"Authorization": f"Bearer {self._settings.read_token}"},
                timeout=self._settings.server_timeout_seconds,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise _TransientRegistryError() from exc

        if response.status_code in TRANSIENT_STATUS_CODES:
            raise _TransientRegistryError(response)
        return response

    def _raise_for_error_response(self, response: httpx.Response) -> None:
        try:
            envelope = ErrorEnvelope.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise UnexpectedRegistryResponseError(
                "Registry returned a malformed error response."
            ) from exc

        code = envelope.error.code
        message = envelope.error.message

        if response.status_code == 404 and code in {"SKILL_VERSION_NOT_FOUND", "SKILL_NOT_FOUND"}:
            raise SkillNotFoundError(message)

        if response.status_code == 422 and code == "INVALID_REQUEST":
            raise InvalidCoordinateError(message)

        if response.status_code in {401, 403}:
            raise RegistryAccessError(message)

        raise UnexpectedRegistryResponseError(message)
