from __future__ import annotations

import os

import pytest

from aptitude_resolver.domain.errors import SkillNotFoundError
from aptitude_resolver.execution.archive import preview_tar_zstd_artifact
from aptitude_resolver.registry.client import RegistryClient
from aptitude_resolver.shared.config import Settings


pytestmark = pytest.mark.integration


APTITUDE_DEMO_SLUG = "python-base"
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
        pytest.skip(
            f"Seeded Aptitude demo coordinate is not present: {slug}@{version}."
        )

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
