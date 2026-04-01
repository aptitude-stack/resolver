from __future__ import annotations

import pytest

from aptitude.domain.errors import VersionConflictError
from aptitude.domain.models import SkillCoordinate
from aptitude.resolution.conflict import ensure_no_version_conflict


def test_ensure_no_version_conflict_allows_matching_versions() -> None:
    selected_versions = {
        "python.lint": SkillCoordinate(slug="python.lint", version="1.2.3")
    }

    ensure_no_version_conflict(
        selected_versions,
        SkillCoordinate(slug="python.lint", version="1.2.3"),
    )


def test_ensure_no_version_conflict_raises_for_same_slug_with_different_versions() -> (
    None
):
    selected_versions = {
        "python.lint": SkillCoordinate(slug="python.lint", version="1.2.3")
    }

    with pytest.raises(VersionConflictError) as exc_info:
        ensure_no_version_conflict(
            selected_versions,
            SkillCoordinate(slug="python.lint", version="2.0.0"),
        )

    payload = exc_info.value.to_payload()
    assert payload["slug"] == "python.lint"
    assert payload["versions"] == ["1.2.3", "2.0.0"]
