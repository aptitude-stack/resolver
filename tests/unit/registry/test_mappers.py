from __future__ import annotations

import pytest

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
    description: str,
    name: str,
    headers: dict[str, object] | None = None,
) -> MetadataResponse:
    return MetadataResponse(
        slug="python.lint",
        version="1.2.3",
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
            inputs_schema={"type": "object"},
            outputs_schema={"type": "object"},
            token_estimate=200,
            maturity_score=0.9,
            security_score=0.95,
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


def test_map_skill_version_list_response_applies_server_defaults() -> None:
    payload = SkillVersionListResponse(
        slug="python.lint",
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

    assert versions[0].coordinate.slug == "python.lint"
    assert versions[0].lifecycle_status == "published"
    assert versions[0].trust_tier == "untrusted"
    assert versions[0].published_at == ""
    assert versions[1].lifecycle_status == "deprecated"
    assert versions[1].trust_tier == "internal"
    assert versions[1].is_current_default is True


def test_dependency_mapping_preserves_selector_contract() -> None:
    selector = DependencySelector(
        slug="dep.core",
        version=None,
        version_constraint=">=1.0",
        optional=True,
        markers=["linux", "ci"],
    )
    payload = DirectDependenciesResponse(
        slug="python.lint",
        version="1.2.3",
        depends_on=[selector],
    )

    mapped_selector = map_dependency_selector(selector)
    mapped_dependencies = map_direct_dependencies(payload)

    assert mapped_selector == DependencySpec(
        slug="dep.core",
        version=None,
        version_constraint=">=1.0",
        optional=True,
        markers=["linux", "ci"],
    )
    assert mapped_dependencies == [mapped_selector]
