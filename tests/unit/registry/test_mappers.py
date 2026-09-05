from __future__ import annotations

import pytest
from pydantic import ValidationError

from aptitude_resolver.domain.models import DependencySpec
from aptitude_resolver.registry.mappers import (
    map_dependency_selector,
    map_direct_dependencies,
    map_metadata_response,
    map_skill_version_list_response,
    map_version_summary,
)
from aptitude_resolver.registry.transport_models import (
    DependencySelector,
    DirectDependenciesResponse,
    MetadataResponse,
    SkillVersionListEntryResponse,
    SkillVersionListResponse,
    TransportChecksum,
    TransportContent,
    TransportMetadata,
)


def _metadata_response(
    *,
    rendered_summary: str | None,
    description: str | None,
    name: str,
    headers: dict[str, object] | None = None,
    overall_score: float | None = None,
) -> MetadataResponse:
    return MetadataResponse(
        slug="python-lint",
        version="1.2.3",
        install_count=123,
        star_count=45,
        content=TransportContent(
            checksum=TransportChecksum(algorithm="sha256", digest="digest-123"),
            size_bytes=79,
            rendered_summary=rendered_summary,
        ),
        metadata=TransportMetadata(
            name=name,
            description=description,
            tags=["python", "lint"],
            headers=dict(headers or {"runtime": "python"}),
            token_estimate=200,
            maturity_score=0.9,
            security_score=0.95,
            overall_score=overall_score,
        ),
        lifecycle_status="published",
        trust_tier="internal",
        published_at="2026-03-18T00:00:00Z",
    )


@pytest.mark.parametrize(
    ("rendered_summary", "description", "name", "expected"),
    [
        ("Rendered summary", "Metadata description", "Python Lint", "Rendered summary"),
        (None, "Metadata description", "Python Lint", "Metadata description"),
        ("", "", "Python Lint", "Python Lint"),
    ],
)
def test_map_metadata_response_uses_summary_fallback_precedence(
    rendered_summary: str | None,
    description: str,
    name: str,
    expected: str,
) -> None:
    payload = _metadata_response(
        rendered_summary=rendered_summary,
        description=description,
        name=name,
    )

    metadata = map_metadata_response(payload)
    version_summary = map_version_summary(payload)

    assert metadata.rendered_summary == expected
    assert version_summary.rendered_summary == expected
    assert metadata.overall_score is None
    assert version_summary.overall_score is None


def test_map_metadata_response_drops_none_headers_and_coerces_other_values() -> None:
    payload = _metadata_response(
        rendered_summary="Rendered summary",
        description="Metadata description",
        name="Python Lint",
        headers={
            "runtime": "python",
            "max_retries": 3,
            "debug": True,
            "omit_me": None,
        },
    )

    metadata = map_metadata_response(payload)

    assert metadata.headers == {
        "runtime": "python",
        "max_retries": "3",
        "debug": "True",
    }


def test_map_metadata_response_preserves_catalog_metrics() -> None:
    payload = _metadata_response(
        rendered_summary="Rendered summary",
        description="Metadata description",
        name="Python Lint",
    )

    metadata = map_metadata_response(payload)
    version_summary = map_version_summary(payload)

    assert metadata.install_count == 123
    assert metadata.star_count == 45
    assert version_summary.install_count == 123
    assert version_summary.star_count == 45


def test_map_metadata_response_preserves_nullable_overall_score() -> None:
    payload = _metadata_response(
        rendered_summary="Rendered summary",
        description="Metadata description",
        name="Python Lint",
        overall_score=0.87,
    )

    metadata = map_metadata_response(payload)
    version_summary = map_version_summary(payload)

    assert metadata.overall_score == 0.87
    assert version_summary.overall_score == 0.87


def test_map_metadata_response_accepts_null_description_for_exact_metadata() -> None:
    payload = _metadata_response(
        rendered_summary=None,
        description=None,
        name="Python Lint",
    )

    metadata = map_metadata_response(payload)

    assert metadata.description == ""
    assert metadata.rendered_summary == "Python Lint"


def test_map_skill_version_list_response_applies_server_defaults() -> None:
    payload = SkillVersionListResponse(
        slug="python-lint",
        versions=[
            SkillVersionListEntryResponse(version="1.2.3"),
            SkillVersionListEntryResponse(
                version="2.0.0",
                lifecycle_status="deprecated",
                trust_tier="internal",
                published_at="2026-03-28T00:00:00Z",
                is_current_default=True,
            ),
        ],
    )

    versions = map_skill_version_list_response(payload)

    assert versions[0].coordinate.slug == "python-lint"
    assert versions[0].lifecycle_status == "published"
    assert versions[0].trust_tier == "untrusted"
    assert versions[0].published_at == ""
    assert versions[1].lifecycle_status == "deprecated"
    assert versions[1].trust_tier == "internal"
    assert versions[1].is_current_default is True


def test_dependency_mapping_preserves_selector_contract() -> None:
    selector = DependencySelector(
        slug="dep-core",
        version=None,
        version_constraint=">=1.0.0",
        optional=True,
        markers=["linux", "ci"],
    )
    payload = DirectDependenciesResponse(
        slug="python-lint",
        version="1.2.3",
        depends_on=[selector],
    )

    mapped_selector = map_dependency_selector(selector)
    mapped_dependencies = map_direct_dependencies(payload)

    assert mapped_selector == DependencySpec(
        slug="dep-core",
        version=None,
            version_constraint=">=1.0.0",
        optional=True,
        markers=["linux", "ci"],
    )
    assert mapped_dependencies == [mapped_selector]


def test_dependency_selector_requires_exactly_one_strict_version_selector() -> None:
    with pytest.raises(ValidationError):
        DependencySelector(slug="dep-core")
    with pytest.raises(ValidationError):
        DependencySelector(
            slug="dep-core",
            version="1.0.0",
            version_constraint=">=1.0.0",
        )
    with pytest.raises(ValidationError):
        DependencySelector(slug="dep-core", version="1.0")


def test_dependency_selector_validates_registry_slug_constraint_and_markers() -> None:
    with pytest.raises(ValidationError):
        DependencySelector(slug="Dep Core", version="1.0.0")
    with pytest.raises(ValidationError):
        DependencySelector(slug="dep-core", version="1.0.0", markers=["bad marker"])

    selector = DependencySelector(
        slug="dep-core",
        version_constraint=">=1.0.0,<2.0.0",
        markers=["linux", "linux", "ci:gpu"],
        optional=None,
    )
    assert selector.optional is False
    assert selector.markers == ["linux", "linux", "ci:gpu"]


def test_dependency_selector_rejects_bare_or_oversized_constraints() -> None:
    with pytest.raises(ValidationError):
        DependencySelector(slug="dep-core", version_constraint="1.0.0")
    with pytest.raises(ValidationError):
        DependencySelector(slug="dep-core", version_constraint="x" * 201)
