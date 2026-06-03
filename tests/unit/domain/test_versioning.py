from __future__ import annotations

import pytest

from aptitude_resolver.domain.versioning import parse_skill_version


def test_parse_skill_version_accepts_registry_semver_prerelease() -> None:
    version = parse_skill_version("0.1.0-publish.20260515115306")

    assert version.raw == "0.1.0-publish.20260515115306"


def test_parse_skill_version_orders_semver_prerelease_before_final() -> None:
    prerelease = parse_skill_version("0.1.0-publish.20260515115306")
    final = parse_skill_version("0.1.0")

    assert prerelease < final


def test_parse_skill_version_accepts_pep440_versions() -> None:
    release_candidate = parse_skill_version("1.0rc1")
    final = parse_skill_version("1.0")

    assert release_candidate < final


def test_parse_skill_version_rejects_unknown_version_schemes() -> None:
    with pytest.raises(ValueError, match="Expected SemVer or PEP 440"):
        parse_skill_version("publish-latest")
