from __future__ import annotations

import pytest

from aptitude_resolver.domain.versioning import (
    parse_semver_constraint,
    parse_skill_version,
)


def test_parse_skill_version_accepts_registry_semver_prerelease() -> None:
    version = parse_skill_version("0.1.0-publish.20260515115306")

    assert version.raw == "0.1.0-publish.20260515115306"


def test_parse_skill_version_orders_semver_prerelease_before_final() -> None:
    prerelease = parse_skill_version("0.1.0-publish.20260515115306")
    final = parse_skill_version("0.1.0")

    assert prerelease < final


@pytest.mark.parametrize(
    "value", ["1.0rc1", "1.0", "1.2.3\n", "publish-latest"]
)
def test_parse_skill_version_rejects_non_semver_versions(value: str) -> None:
    with pytest.raises(ValueError, match="Expected strict SemVer"):
        parse_skill_version(value)


def test_semver_constraint_requires_comparators_and_supports_build_metadata() -> None:
    constraint = parse_semver_constraint(">=1.0.0+ignored,<2.0.0")

    assert constraint.contains("1.5.0+lookup")
    assert not constraint.contains("2.0.0")


def test_semver_build_metadata_is_ignored_for_ordering_and_hashing() -> None:
    first = parse_skill_version("1.2.3+build.1")
    second = parse_skill_version("1.2.3+build.2")

    assert first == second
    assert hash(first) == hash(second)
    assert first.raw == "1.2.3+build.1"


@pytest.mark.parametrize(
    "value",
    [
        "1.0.0",
        ">=1.0",
        ">=1.0.0,,<2.0.0",
        ">=1.0.0\n",
        ">=latest",
        "",
    ],
)
def test_parse_semver_constraint_rejects_non_strict_constraints(value: str) -> None:
    with pytest.raises(ValueError):
        parse_semver_constraint(value)
