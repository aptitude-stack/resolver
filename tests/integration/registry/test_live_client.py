from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

import httpx
import pytest

from aptitude_client.domain.errors import InvalidCoordinateError, SkillNotFoundError
from aptitude_client.registry.client import RegistryClient
from aptitude_client.shared.config import Settings


pytestmark = pytest.mark.integration


def _require_integration_enabled() -> None:
    if os.getenv("APTITUDE_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Set APTITUDE_RUN_INTEGRATION=1 to run live Aptitude server integration tests."
        )


@dataclass(frozen=True)
class IntegrationConfig:
    """Runtime configuration for live server integration tests."""

    base_url: str
    read_token: str
    publish_token: str
    timeout_seconds: float


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
def integration_config() -> IntegrationConfig:
    _require_integration_enabled()

    return IntegrationConfig(
        base_url=os.getenv("APTITUDE_INTEGRATION_BASE_URL", "http://localhost:8000"),
        read_token=os.getenv("APTITUDE_INTEGRATION_READ_TOKEN", "reader-token"),
        publish_token=os.getenv("APTITUDE_INTEGRATION_PUBLISH_TOKEN", "publisher-token"),
        timeout_seconds=float(os.getenv("APTITUDE_INTEGRATION_TIMEOUT_SECONDS", "5.0")),
    )


@pytest.fixture(scope="session")
def integration_settings(integration_config: IntegrationConfig) -> Settings:
    return Settings(
        server_base_url=integration_config.base_url,
        read_token=integration_config.read_token,
        server_timeout_seconds=integration_config.timeout_seconds,
    )


@pytest.fixture(scope="session")
def published_skill_set(integration_config: IntegrationConfig) -> PublishedSkillSet:
    run_id = uuid.uuid4().hex
    dependency_slug = f"it.dep.{run_id}"
    primary_slug = f"it.primary.{run_id}"
    dependency_name = f"Integration Dependency Skill {run_id}"
    primary_name = f"Integration Primary Skill {run_id}"
    version = "1.0.0"

    publish_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {integration_config.publish_token}",
    }

    dependency_payload = {
        "slug": dependency_slug,
        "version": version,
        "content": {
            "raw_markdown": f"# {dependency_name}\n\nRun `{run_id}` dependency version 1.\n",
            "rendered_summary": "Integration dependency skill.",
        },
        "metadata": {
            "name": dependency_name,
            "description": f"Dependency seed for registry adapter integration tests ({run_id})",
            "tags": ["integration", "dependency", run_id],
            "headers": {"runtime": "python"},
            "inputs_schema": {"type": "object"},
            "outputs_schema": {"type": "object"},
            "token_estimate": 110,
            "maturity_score": 0.8,
            "security_score": 0.9,
        },
        "relationships": {
            "depends_on": [],
            "extends": [],
            "conflicts_with": [],
            "overlaps_with": [],
        },
    }

    primary_payload = {
        "slug": primary_slug,
        "version": version,
        "content": {
            "raw_markdown": f"# {primary_name}\n\nRun `{run_id}` primary version 1.\n",
            "rendered_summary": "Integration primary skill.",
        },
        "metadata": {
            "name": primary_name,
            "description": f"Primary seed for registry adapter integration tests ({run_id})",
            "tags": ["integration", "primary", run_id],
            "headers": {"runtime": "python"},
            "inputs_schema": {"type": "object"},
            "outputs_schema": {"type": "object"},
            "token_estimate": 210,
            "maturity_score": 0.9,
            "security_score": 0.95,
        },
        "relationships": {
            "depends_on": [
                {
                    "slug": dependency_slug,
                    "version": version,
                    "optional": False,
                    "markers": ["linux"],
                }
            ],
            "extends": [],
            "conflicts_with": [],
            "overlaps_with": [],
        },
    }

    with httpx.Client(
        base_url=integration_config.base_url,
        timeout=integration_config.timeout_seconds,
    ) as client:
        dependency_response = client.post(
            "/skill-versions",
            headers=publish_headers,
            json=dependency_payload,
        )
        assert dependency_response.status_code == 201, dependency_response.text

        primary_response = client.post(
            "/skill-versions",
            headers=publish_headers,
            json=primary_payload,
        )
        assert primary_response.status_code == 201, primary_response.text

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
