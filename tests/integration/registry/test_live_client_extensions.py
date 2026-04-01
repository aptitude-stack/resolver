from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

import httpx
import pytest

from aptitude.domain.models import DiscoveryQuery
from aptitude.registry.client import RegistryClient
from aptitude.shared.config import Settings


pytestmark = pytest.mark.integration


def _require_integration_enabled() -> None:
    if os.getenv("APTITUDE_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Set APTITUDE_RUN_INTEGRATION=1 to run live Aptitude server integration tests."
        )


@dataclass(frozen=True)
class IntegrationConfig:
    base_url: str
    read_token: str
    publish_token: str
    timeout_seconds: float


@dataclass(frozen=True)
class PublishedSkill:
    slug: str
    name: str
    version: str
    content: str


@pytest.fixture(scope="session")
def integration_config() -> IntegrationConfig:
    _require_integration_enabled()
    return IntegrationConfig(
        base_url=os.getenv("APTITUDE_INTEGRATION_BASE_URL", "http://localhost:8000"),
        read_token=os.getenv("APTITUDE_INTEGRATION_READ_TOKEN", "reader-token"),
        publish_token=os.getenv(
            "APTITUDE_INTEGRATION_PUBLISH_TOKEN", "publisher-token"
        ),
        timeout_seconds=float(os.getenv("APTITUDE_INTEGRATION_TIMEOUT_SECONDS", "5.0")),
    )


@pytest.fixture(scope="session")
def integration_settings(integration_config: IntegrationConfig) -> Settings:
    return Settings(
        server_base_url=integration_config.base_url,
        read_token=integration_config.read_token,
        server_timeout_seconds=integration_config.timeout_seconds,
        _env_file=None,
    )


@pytest.fixture(scope="session")
def published_skill(integration_config: IntegrationConfig) -> PublishedSkill:
    run_id = uuid.uuid4().hex
    slug = f"it.discovery.{run_id}"
    name = f"Integration Discovery Skill {run_id}"
    version = "1.0.0"
    content = f"# {name}\n\nRun `{run_id}` discovery version 1.\n"

    publish_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {integration_config.publish_token}",
    }
    payload = {
        "slug": slug,
        "version": version,
        "content": {
            "raw_markdown": content,
            "rendered_summary": "Integration discovery skill.",
        },
        "metadata": {
            "name": name,
            "description": f"Discovery seed for registry adapter integration tests ({run_id})",
            "tags": ["integration", "discovery", run_id],
            "headers": {"runtime": "python"},
            "inputs_schema": {"type": "object"},
            "outputs_schema": {"type": "object"},
            "token_estimate": 120,
            "maturity_score": 0.9,
            "security_score": 0.95,
        },
        "relationships": {
            "depends_on": [],
            "extends": [],
            "conflicts_with": [],
            "overlaps_with": [],
        },
    }

    with httpx.Client(
        base_url=integration_config.base_url,
        timeout=integration_config.timeout_seconds,
    ) as client:
        response = client.post(
            "/skill-versions",
            headers=publish_headers,
            json=payload,
        )
        assert response.status_code == 201, response.text

    return PublishedSkill(slug=slug, name=name, version=version, content=content)


def test_fetch_skill_identity_against_live_server(
    integration_settings: Settings,
    published_skill: PublishedSkill,
) -> None:
    client = RegistryClient(integration_settings)

    identity = client.fetch_skill_identity(published_skill.slug)

    assert identity.slug == published_skill.slug
    assert identity.status
    assert identity.current_version is not None
    assert identity.current_version.version == published_skill.version


def test_list_skill_versions_against_live_server(
    integration_settings: Settings,
    published_skill: PublishedSkill,
) -> None:
    client = RegistryClient(integration_settings)

    versions = client.list_skill_versions(published_skill.slug)

    assert [item.coordinate.version for item in versions] == [published_skill.version]
    assert versions[0].name == published_skill.name


def test_fetch_skill_content_against_live_server(
    integration_settings: Settings,
    published_skill: PublishedSkill,
) -> None:
    client = RegistryClient(integration_settings)

    content = client.fetch_skill_content(published_skill.slug, published_skill.version)

    assert content == published_skill.content


def test_discover_candidate_slugs_against_live_server(
    integration_settings: Settings,
    published_skill: PublishedSkill,
) -> None:
    client = RegistryClient(integration_settings)

    candidates = client.discover_candidate_slugs(
        DiscoveryQuery(
            name=published_skill.name,
            description=published_skill.name,
            tags=["integration", "discovery"],
        )
    )

    assert published_skill.slug in candidates
