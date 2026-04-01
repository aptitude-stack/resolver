from __future__ import annotations

import pytest

from aptitude_client.domain.errors import UnsupportedDependencyShapeError
from aptitude_client.domain.models import DependencySpec, SkillCoordinate
from aptitude_client.resolver.normalizer import normalize_dependency_selector


def test_normalize_dependency_selector_returns_exact_coordinate_when_version_is_present() -> (
    None
):
    coordinate = normalize_dependency_selector(
        SkillCoordinate(slug="root.skill", version="1.0.0"),
        DependencySpec(
            slug="dep.skill",
            version="2.3.4",
            version_constraint=">=2.0.0",
            optional=True,
            markers=["python>=3.11"],
        ),
    )

    assert coordinate == SkillCoordinate(slug="dep.skill", version="2.3.4")


def test_normalize_dependency_selector_rejects_non_exact_selector_shapes() -> None:
    with pytest.raises(UnsupportedDependencyShapeError) as exc_info:
        normalize_dependency_selector(
            SkillCoordinate(slug="root.skill", version="1.0.0"),
            DependencySpec(slug="dep.skill", version_constraint=">=2.0.0"),
        )

    payload = exc_info.value.to_payload()
    assert payload["slug"] == "root.skill"
    assert payload["version"] == "1.0.0"
    assert "exact dependency versions" in payload["details"]
