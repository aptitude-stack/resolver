from __future__ import annotations

import tempfile
from pathlib import Path

import httpx
import pytest

from aptitude_resolver.cache import CacheStore
from aptitude_resolver.domain.errors import RegistryUnavailableError, SkillNotFoundError
from aptitude_resolver.registry.client import RegistryClient
from aptitude_resolver.shared.config import Settings


def _settings() -> Settings:
    return Settings(
        server_base_url="http://testserver",
        read_token="reader-token",
        server_timeout_seconds=5.0,
        _env_file=None,
    )


def _client(handler, *, cache_dir=None) -> RegistryClient:
    return RegistryClient(
        _settings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        cache_store=CacheStore(
            cache_dir or Path(tempfile.mkdtemp(prefix="resolver-cache-test-"))
        ),
    )


def test_list_skill_versions_reads_live_contract_from_versions_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/skills/postman.primary.1774130709214-55706/versions"
        return httpx.Response(
            200,
            json={
                "slug": "postman.primary.1774130709214-55706",
                "versions": [
                    {
                        "version": "1.0.0",
                        "lifecycle_status": "published",
                        "trust_tier": "internal",
                        "published_at": "2026-03-21T22:05:11.334228Z",
                        "is_current_default": True,
                    },
                    {
                        "version": "2.0.0",
                        "lifecycle_status": "deprecated",
                        "trust_tier": "internal",
                        "published_at": "2026-03-21T22:05:11.555700Z",
                        "is_current_default": False,
                    },
                ],
            },
        )

    client = _client(handler)

    versions = client.list_skill_versions("postman.primary.1774130709214-55706")

    assert [item.coordinate.version for item in versions] == ["1.0.0", "2.0.0"]
    assert versions[0].coordinate.slug == "postman.primary.1774130709214-55706"
    assert versions[0].is_current_default is True


def test_fetch_skill_identity_uses_version_list_endpoint_as_exact_slug_probe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/skills/postman.primary.1774130709214-55706/versions"
        return httpx.Response(
            200,
            json={
                "slug": "postman.primary.1774130709214-55706",
                "versions": [
                    {
                        "version": "1.0.0",
                        "lifecycle_status": "published",
                        "trust_tier": "internal",
                        "published_at": "2026-03-21T22:05:11.334228Z",
                        "is_current_default": True,
                    }
                ],
            },
        )

    client = _client(handler)

    identity = client.fetch_skill_identity("postman.primary.1774130709214-55706")

    assert identity.slug == "postman.primary.1774130709214-55706"
    assert identity.current_version is not None
    assert identity.current_version.version == "1.0.0"
    assert identity.current_lifecycle_status == "published"
    assert identity.current_trust_tier == "internal"


def test_fetch_skill_metadata_uses_live_exact_metadata_path_and_falls_back_summary() -> (
    None
):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/skills/postman.primary.1774130709214-55706/versions/1.0.0"
        return httpx.Response(
            200,
            json={
                "slug": "postman.primary.1774130709214-55706",
                "version": "1.0.0",
                "version_checksum": {
                    "algorithm": "sha256",
                    "digest": "a98906f17fa4fce41b159b35aa848de2bb4f4049a7318764e437abb630c94d18",
                },
                "content": {
                    "checksum": {
                        "algorithm": "sha256",
                        "digest": "a98906f17fa4fce41b159b35aa848de2bb4f4049a7318764e437abb630c94d18",
                    },
                    "size_bytes": 79,
                },
                "metadata": {
                    "name": "Postman Primary Skill",
                    "description": "Primary sanity skill for collection coverage",
                    "tags": ["postman", "sanity", "primary"],
                    "headers": {"runtime": "python"},
                    "inputs_schema": {"type": "object"},
                    "outputs_schema": {"type": "object"},
                    "token_estimate": 200,
                    "maturity_score": 0.9,
                    "security_score": 0.95,
                },
                "lifecycle_status": "published",
                "trust_tier": "internal",
                "published_at": "2026-03-21T22:05:11.334228Z",
            },
        )

    client = _client(handler)

    metadata = client.fetch_skill_metadata(
        "postman.primary.1774130709214-55706", "1.0.0"
    )

    assert metadata.coordinate.slug == "postman.primary.1774130709214-55706"
    assert metadata.coordinate.version == "1.0.0"
    assert metadata.name == "Postman Primary Skill"
    assert metadata.rendered_summary == "Primary sanity skill for collection coverage"


def test_fetch_skill_artifact_uses_live_content_path_for_binary_payload() -> None:
    artifact = b"zstd artifact bytes"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/skills/postman.primary.1774130709214-55706/versions/1.0.0/content"
        return httpx.Response(200, content=artifact)

    client = _client(handler)

    content = client.fetch_skill_artifact(
        "postman.primary.1774130709214-55706", "1.0.0"
    )

    assert content == artifact


def test_list_skill_versions_falls_back_to_legacy_skill_identity_endpoint_when_canonical_path_is_rejected() -> None:
    request_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_paths.append(request.url.path)
        if request.url.path == "/skills/postman.primary.1774130709214-55706/versions":
            return httpx.Response(
                422,
                json={"error": {"code": "INVALID_REQUEST", "message": "Request validation failed."}},
            )
        assert request.url.path == "/skills/postman.primary.1774130709214-55706"
        return httpx.Response(
            200,
            json={
                "slug": "postman.primary.1774130709214-55706",
                "versions": [
                    {
                        "version": "1.0.0",
                        "lifecycle_status": "published",
                        "trust_tier": "internal",
                        "published_at": "2026-03-21T22:05:11.334228Z",
                        "is_current_default": True,
                    }
                ],
            },
        )

    client = _client(handler)

    versions = client.list_skill_versions("postman.primary.1774130709214-55706")

    assert [item.coordinate.version for item in versions] == ["1.0.0"]
    assert request_paths == [
        "/skills/postman.primary.1774130709214-55706/versions",
        "/skills/postman.primary.1774130709214-55706",
    ]


def test_fetch_skill_metadata_falls_back_to_legacy_exact_metadata_endpoint_when_needed() -> None:
    request_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_paths.append(request.url.path)
        if request.url.path == "/skills/postman.primary.1774130709214-55706/versions/1.0.0":
            return httpx.Response(
                422,
                json={"error": {"code": "INVALID_REQUEST", "message": "Request validation failed."}},
            )
        assert request.url.path == "/skills/postman.primary.1774130709214-55706/1.0.0"
        return httpx.Response(
            200,
            json={
                "slug": "postman.primary.1774130709214-55706",
                "version": "1.0.0",
                "content": {
                    "checksum": {
                        "algorithm": "sha256",
                        "digest": "a98906f17fa4fce41b159b35aa848de2bb4f4049a7318764e437abb630c94d18",
                    },
                    "size_bytes": 79,
                },
                "metadata": {
                    "name": "Postman Primary Skill",
                    "description": "Primary sanity skill for collection coverage",
                    "tags": ["postman", "sanity", "primary"],
                    "headers": {"runtime": "python"},
                },
                "lifecycle_status": "published",
                "trust_tier": "internal",
                "published_at": "2026-03-21T22:05:11.334228Z",
            },
        )

    client = _client(handler)

    metadata = client.fetch_skill_metadata("postman.primary.1774130709214-55706", "1.0.0")

    assert metadata.coordinate.version == "1.0.0"
    assert metadata.name == "Postman Primary Skill"
    assert request_paths == [
        "/skills/postman.primary.1774130709214-55706/versions/1.0.0",
        "/skills/postman.primary.1774130709214-55706/1.0.0",
    ]


def test_fetch_skill_artifact_falls_back_to_legacy_content_endpoint_when_needed() -> None:
    artifact = b"legacy artifact bytes"
    request_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_paths.append(request.url.path)
        if request.url.path == "/skills/postman.primary.1774130709214-55706/versions/1.0.0/content":
            return httpx.Response(
                422,
                json={"error": {"code": "INVALID_REQUEST", "message": "Request validation failed."}},
            )
        assert (
            request.url.path
            == "/skills/postman.primary.1774130709214-55706/1.0.0/content"
        )
        return httpx.Response(200, content=artifact)

    client = _client(handler)

    content = client.fetch_skill_artifact(
        "postman.primary.1774130709214-55706", "1.0.0"
    )

    assert content == artifact
    assert request_paths == [
        "/skills/postman.primary.1774130709214-55706/versions/1.0.0/content",
        "/skills/postman.primary.1774130709214-55706/1.0.0/content",
    ]


def test_list_skill_versions_uses_advisory_cache_for_repeat_reads(tmp_path) -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={
                "slug": "python.lint",
                "versions": [
                    {
                        "version": "1.2.3",
                        "lifecycle_status": "published",
                        "trust_tier": "internal",
                        "published_at": "2026-03-28T00:00:00Z",
                        "is_current_default": True,
                    }
                ],
            },
        )

    client = _client(handler, cache_dir=tmp_path / "cache")

    first = client.list_skill_versions("python.lint")
    second = client.list_skill_versions("python.lint")

    assert [item.coordinate.version for item in first] == ["1.2.3"]
    assert [item.coordinate.version for item in second] == ["1.2.3"]
    assert request_count == 1


def test_fetch_skill_artifact_uses_checksum_cache_key_when_available(tmp_path) -> None:
    artifact = b"cached artifact bytes"
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, content=artifact)

    client = _client(handler, cache_dir=tmp_path / "cache")

    first = client.fetch_skill_artifact(
        "python.lint",
        "1.2.3",
        checksum_algorithm="sha256",
        checksum_digest="digest-123",
    )
    second = client.fetch_skill_artifact(
        "python.lint",
        "1.2.3",
        checksum_algorithm="sha256",
        checksum_digest="digest-123",
    )

    assert first == artifact
    assert second == artifact
    assert request_count == 1


def test_registry_client_retries_transient_server_failures_then_succeeds() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count < 3:
            return httpx.Response(
                503, json={"error": {"code": "TEMPORARY", "message": "retry"}}
            )
        return httpx.Response(
            200,
            json={
                "slug": "python.lint",
                "versions": [
                    {
                        "version": "1.2.3",
                        "lifecycle_status": "published",
                        "trust_tier": "internal",
                        "published_at": "2026-03-28T00:00:00Z",
                        "is_current_default": True,
                    }
                ],
            },
        )

    client = _client(handler)

    versions = client.list_skill_versions("python.lint")

    assert [item.coordinate.version for item in versions] == ["1.2.3"]
    assert request_count == 3


def test_registry_client_does_not_retry_non_transient_not_found_errors() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            404,
            json={"error": {"code": "SKILL_NOT_FOUND", "message": "missing"}},
        )

    client = _client(handler)

    with pytest.raises(SkillNotFoundError, match="missing"):
        client.list_skill_versions("missing.skill")

    assert request_count == 1


def test_registry_client_raises_unavailable_after_exhausting_transient_retries() -> (
    None
):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            503,
            json={"error": {"code": "TEMPORARY", "message": "retry"}},
        )

    client = _client(handler)

    with pytest.raises(RegistryUnavailableError, match="Registry is unavailable"):
        client.list_skill_versions("python.lint")

    assert request_count == 3
