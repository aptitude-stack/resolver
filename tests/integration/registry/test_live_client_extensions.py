from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx
import pytest

from aptitude_resolver.domain.models import DiscoveryQuery
from aptitude_resolver.registry.client import RegistryClient
from aptitude_resolver.shared.config import Settings
from integration.registry.support import build_publish_payload, ensure_publish_ready


pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class PublishedSkill:
    slug: str
    name: str
    version: str
    content: str


@pytest.fixture(scope="session")
def published_skill(integration_config, publish_token: str) -> PublishedSkill:
    run_id = uuid.uuid4().hex
    slug = f"it.discovery.{run_id}"
    name = f"Integration Discovery Skill {run_id}"
    version = "1.0.0"
    content = f"# {name}\n\nRun `{run_id}` discovery version 1.\n"

    publish_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {publish_token}",
    }
    payload = build_publish_payload(
        version=version,
        raw_markdown=content,
        name=name,
        description=f"Discovery seed for registry adapter integration tests ({run_id})",
        tags=["integration", "discovery", run_id],
        token_estimate=120,
        maturity_score=0.9,
        security_score=0.95,
    )

    with httpx.Client(
        base_url=integration_config.base_url,
        timeout=integration_config.timeout_seconds,
    ) as client:
        response = client.post(
            f"/skills/{slug}",
            headers=publish_headers,
            json=payload,
        )
        ensure_publish_ready(response)

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
    assert versions[0].coordinate.slug == published_skill.slug
    assert versions[0].is_current_default is True


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
