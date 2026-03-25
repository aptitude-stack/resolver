from __future__ import annotations

import httpx

from aptitude_client.registry.client import RegistryClient
from aptitude_client.shared.config import Settings


def _settings() -> Settings:
    return Settings(
        server_base_url="http://testserver",
        read_token="reader-token",
        server_timeout_seconds=5.0,
        _env_file=None,
    )


def test_list_skill_versions_reads_live_contract_from_skills_slug_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
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

    client = RegistryClient(
        _settings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    versions = client.list_skill_versions("postman.primary.1774130709214-55706")

    assert [item.coordinate.version for item in versions] == ["1.0.0", "2.0.0"]
    assert versions[0].coordinate.slug == "postman.primary.1774130709214-55706"
    assert versions[0].is_current_default is True


def test_fetch_skill_identity_uses_version_list_endpoint_as_exact_slug_probe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
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

    client = RegistryClient(
        _settings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    identity = client.fetch_skill_identity("postman.primary.1774130709214-55706")

    assert identity.slug == "postman.primary.1774130709214-55706"
    assert identity.current_version is not None
    assert identity.current_version.version == "1.0.0"
    assert identity.current_lifecycle_status == "published"
    assert identity.current_trust_tier == "internal"


def test_fetch_skill_metadata_uses_live_exact_metadata_path_and_falls_back_summary() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/skills/postman.primary.1774130709214-55706/1.0.0"
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

    client = RegistryClient(
        _settings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    metadata = client.fetch_skill_metadata("postman.primary.1774130709214-55706", "1.0.0")

    assert metadata.coordinate.slug == "postman.primary.1774130709214-55706"
    assert metadata.coordinate.version == "1.0.0"
    assert metadata.name == "Postman Primary Skill"
    assert metadata.rendered_summary == "Primary sanity skill for collection coverage"


def test_fetch_skill_content_uses_live_content_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/skills/postman.primary.1774130709214-55706/1.0.0/content"
        return httpx.Response(200, text="# Postman Primary Skill v1\n")

    client = RegistryClient(
        _settings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    content = client.fetch_skill_content("postman.primary.1774130709214-55706", "1.0.0")

    assert content == "# Postman Primary Skill v1\n"
