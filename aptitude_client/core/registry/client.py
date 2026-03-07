"""HTTP client for Aptitude registry discovery endpoints."""

from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from aptitude_client.core.registry.contracts import GetSkillResponse, ListSkillsResponse
from aptitude_client.core.registry.errors import (
    RegistryHTTPError,
    RegistryResponseError,
    RegistryTransportError,
)
from aptitude_client.models import SkillManifest, SkillSummary


class RegistryClient:
    """Client for skill-discovery endpoints exposed by the Aptitude registry."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        *,
        client: Optional[httpx.Client] = None,
        headers: Optional[Mapping[str, str]] = None,
        auth_token: Optional[str] = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=self._build_headers(headers=headers, auth_token=auth_token),
        )

    def close(self) -> None:
        """Close the underlying HTTP client when owned by this instance."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "RegistryClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def list_skills(self) -> List[SkillSummary]:
        """Fetch `GET /skills` and return parsed skill summaries."""
        payload = self._request_json("GET", "/skills")
        try:
            response_model = ListSkillsResponse.model_validate(payload)
        except ValidationError as exc:
            raise RegistryResponseError(f"Response validation failed for GET /skills: {exc}") from exc
        return response_model.skills

    def get_skill(self, name: str) -> SkillManifest:
        """Fetch `GET /skills/{name}` and return a parsed skill manifest."""
        endpoint = f"/skills/{quote(name, safe='')}"
        payload = self._request_json("GET", endpoint)
        try:
            response_model = GetSkillResponse.model_validate(payload)
        except ValidationError as exc:
            raise RegistryResponseError(f"Response validation failed for GET {endpoint}: {exc}") from exc
        return response_model.skill

    def get_skill_version(self, name: str, version: str) -> SkillManifest:
        """Fetch `GET /skills/{name}/{version}` and return a parsed manifest."""
        endpoint = f"/skills/{quote(name, safe='')}/{quote(version, safe='')}"
        payload = self._request_json("GET", endpoint)
        try:
            response_model = GetSkillResponse.model_validate(payload)
        except ValidationError as exc:
            raise RegistryResponseError(f"Response validation failed for GET {endpoint}: {exc}") from exc
        return response_model.skill

    @staticmethod
    def _build_headers(
        *, headers: Optional[Mapping[str, str]], auth_token: Optional[str]
    ) -> Dict[str, str]:
        merged_headers: Dict[str, str] = {}
        if headers:
            merged_headers.update(headers)
        if auth_token:
            merged_headers["Authorization"] = f"Bearer {auth_token}"
        return merged_headers

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Mapping[str, str]] = None,
    ) -> Any:
        try:
            response = self._client.request(method=method, url=endpoint, params=params)
        except httpx.HTTPError as exc:
            raise RegistryTransportError(f"Request failed for {method} {endpoint}: {exc}") from exc

        if response.status_code >= 400:
            raise self._build_http_error(response=response)

        try:
            return response.json()
        except ValueError as exc:
            raise RegistryResponseError(
                f"Expected JSON response for {method} {endpoint}, but got invalid JSON."
            ) from exc

    @staticmethod
    def _build_http_error(response: httpx.Response) -> RegistryHTTPError:
        message = f"Request failed for {response.request.method} {response.request.url.path}"
        error_code: Optional[str] = None
        details: Optional[Any] = None

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            message = str(payload.get("message") or payload.get("error") or message)
            error_code_value = payload.get("code")
            if error_code_value is not None:
                error_code = str(error_code_value)
            details = payload.get("details")

        return RegistryHTTPError(
            status_code=response.status_code,
            message=message,
            error_code=error_code,
            details=details,
        )
