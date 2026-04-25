from __future__ import annotations

import os

import pytest

from aptitude_resolver.domain.errors import InvalidArtifactError, SkillNotFoundError
from aptitude_resolver.execution.archive import preview_tar_zstd_artifact
from aptitude_resolver.registry.client import RegistryClient
from aptitude_resolver.shared.config import Settings


pytestmark = pytest.mark.integration


POSTMAN_PRIMARY_SLUG = "postman.primary.1775674127381-77801"
POSTMAN_PRIMARY_VERSION = "1.0.0"
APTITUDE_DEMO_SLUG = "python.base"
APTITUDE_DEMO_VERSION = "1.1.0"


def test_seeded_aptitude_demo_artifact_downloads_as_tar_zst_against_live_server(
    integration_settings: Settings,
) -> None:
    """Download a seeded Aptitude skill artifact from the server and read it as tar.zst."""

    slug = os.getenv("APTITUDE_DEMO_ARTIFACT_SLUG", APTITUDE_DEMO_SLUG)
    version = os.getenv("APTITUDE_DEMO_ARTIFACT_VERSION", APTITUDE_DEMO_VERSION)
    client = RegistryClient(integration_settings)

    try:
        metadata = client.fetch_skill_metadata(slug, version)
    except SkillNotFoundError:
        pytest.skip(f"Seeded Aptitude demo coordinate is not present: {slug}@{version}.")

    artifact = client.fetch_skill_artifact(
        slug,
        version,
        checksum_algorithm=metadata.content_checksum_algorithm,
        checksum_digest=metadata.content_checksum_digest,
    )
    preview, truncated = preview_tar_zstd_artifact(
        slug=slug,
        version=version,
        artifact=artifact,
        limit=300,
    )

    assert artifact.startswith(b"\x28\xb5\x2f\xfd")
    assert "# Python Base Runtime" in preview
    assert truncated is True


def test_seeded_postman_primary_artifact_is_not_tar_zst_against_live_server(
    integration_settings: Settings,
) -> None:
    """Show the current seeded Postman artifact is not a readable tar.zst bundle.

    This is a read-only contract check. It uses only APTITUDE_READ_TOKEN and does
    not publish or mutate server state.
    """

    slug = os.getenv("APTITUDE_POSTMAN_ARTIFACT_SLUG", POSTMAN_PRIMARY_SLUG)
    version = os.getenv("APTITUDE_POSTMAN_ARTIFACT_VERSION", POSTMAN_PRIMARY_VERSION)
    client = RegistryClient(integration_settings)

    try:
        metadata = client.fetch_skill_metadata(slug, version)
    except SkillNotFoundError:
        pytest.skip(f"Seeded Postman coordinate is not present: {slug}@{version}.")

    artifact = client.fetch_skill_artifact(
        slug,
        version,
        checksum_algorithm=metadata.content_checksum_algorithm,
        checksum_digest=metadata.content_checksum_digest,
    )

    assert artifact
    with pytest.raises(InvalidArtifactError, match="not a readable tar.zst archive"):
        preview_tar_zstd_artifact(
            slug=slug,
            version=version,
            artifact=artifact,
            limit=200,
        )
