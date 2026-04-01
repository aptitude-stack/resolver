from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx
import pytest

from aptitude.domain.errors import InvalidCoordinateError, SkillNotFoundError
from aptitude.registry.client import RegistryClient
from aptitude.shared.config import Settings
from integration.registry.support import build_publish_payload, ensure_publish_ready


pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class PublishedSkillSet:
    """Published exact coordinates used by the live integration tests."""

    dependency_slug: str
    dependency_name: str
    dependency_version: str
    primary_slug: str
    primary_name: str
    primary_version: str


@pytest.fixture(scope="session")
def published_skill_set(integration_config, publish_token: str) -> PublishedSkillSet:
    run_id = uuid.uuid4().hex
    dependency_slug = f"it.dep.{run_id}"
    primary_slug = f"it.primary.{run_id}"
    dependency_name = f"Integration Dependency Skill {run_id}"
    primary_name = f"Integration Primary Skill {run_id}"
    version = "1.0.0"

    publish_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {publish_token}",
    }

    dependency_payload = build_publish_payload(
        version=version,
        raw_markdown=f"# {dependency_name}\n\nRun `{run_id}` dependency version 1.\n",
        name=dependency_name,
        description=f"Dependency seed for registry adapter integration tests ({run_id})",
        tags=["integration", "dependency", run_id],
        token_estimate=110,
        maturity_score=0.8,
        security_score=0.9,
    )

    primary_payload = build_publish_payload(
        version=version,
        raw_markdown=f"# {primary_name}\n\nRun `{run_id}` primary version 1.\n",
        name=primary_name,
        description=f"Primary seed for registry adapter integration tests ({run_id})",
        tags=["integration", "primary", run_id],
        token_estimate=210,
        maturity_score=0.9,
        security_score=0.95,
        depends_on=[
            {
                "slug": dependency_slug,
                "version": version,
                "optional": False,
                "markers": ["linux"],
            }
        ],
    )

    with httpx.Client(
        base_url=integration_config.base_url,
        timeout=integration_config.timeout_seconds,
    ) as client:
        dependency_response = client.post(
            f"/skills/{dependency_slug}",
            headers=publish_headers,
            json=dependency_payload,
        )
        ensure_publish_ready(dependency_response)

        primary_response = client.post(
            f"/skills/{primary_slug}",
            headers=publish_headers,
            json=primary_payload,
        )
        ensure_publish_ready(primary_response)

    return PublishedSkillSet(
        dependency_slug=dependency_slug,
        dependency_name=dependency_name,
        dependency_version=version,
        primary_slug=primary_slug,
        primary_name=primary_name,
        primary_version=version,
    )


def test_fetch_skill_metadata_against_live_server(
    integration_settings: Settings,
    published_skill_set: PublishedSkillSet,
) -> None:
    client = RegistryClient(integration_settings)

    metadata = client.fetch_skill_metadata(
        published_skill_set.primary_slug,
        published_skill_set.primary_version,
    )

    assert metadata.coordinate.slug == published_skill_set.primary_slug
    assert metadata.coordinate.version == published_skill_set.primary_version
    assert metadata.name == published_skill_set.primary_name
    assert metadata.description == (
        f"Primary seed for registry adapter integration tests ({published_skill_set.primary_slug.split('.')[-1]})"
    )
    assert metadata.content_checksum_algorithm == "sha256"
    assert metadata.content_checksum_digest
    assert metadata.lifecycle_status == "published"
    assert metadata.published_at


def test_fetch_direct_dependencies_against_live_server(
    integration_settings: Settings,
    published_skill_set: PublishedSkillSet,
) -> None:
    client = RegistryClient(integration_settings)

    dependencies = client.fetch_direct_dependencies(
        published_skill_set.primary_slug,
        published_skill_set.primary_version,
    )

    assert len(dependencies) == 1
    dependency = dependencies[0]
    assert dependency.slug == published_skill_set.dependency_slug
    assert dependency.version == published_skill_set.dependency_version
    assert dependency.optional is False
    assert dependency.markers == ["linux"]


def test_discover_candidates_against_live_server(
    integration_settings: Settings,
    published_skill_set: PublishedSkillSet,
) -> None:
    client = RegistryClient(integration_settings)

    candidates = client.discover_candidates(published_skill_set.primary_name)

    assert published_skill_set.primary_slug in candidates


def test_fetch_missing_coordinate_against_live_server(
    integration_settings: Settings,
) -> None:
    client = RegistryClient(integration_settings)

    with pytest.raises(SkillNotFoundError):
        client.fetch_skill_metadata(f"it.missing.{uuid.uuid4().hex}", "9.9.9")


def test_fetch_invalid_version_against_live_server(
    integration_settings: Settings,
) -> None:
    client = RegistryClient(integration_settings)

    with pytest.raises(InvalidCoordinateError):
        client.fetch_skill_metadata("python.lint", "not-a-semver")
