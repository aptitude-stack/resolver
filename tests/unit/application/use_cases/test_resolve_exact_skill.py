from __future__ import annotations

from aptitude_client.application.dto import ResolveRequestDto
from aptitude_client.application.use_cases import ResolveExactSkillUseCase
from aptitude_client.domain.errors import SkillNotFoundError
from aptitude_client.domain.models import DependencySpec, SkillCoordinate, SkillMetadata


class FakeRegistryClient:
    def __init__(
        self,
        *,
        metadata: SkillMetadata | None = None,
        dependencies: list[DependencySpec] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.metadata = metadata
        self.dependencies = dependencies or []
        self.error = error
        self.metadata_calls: list[tuple[str, str]] = []
        self.dependency_calls: list[tuple[str, str]] = []

    def fetch_skill_metadata(self, slug: str, version: str) -> SkillMetadata:
        self.metadata_calls.append((slug, version))
        if self.error is not None:
            raise self.error
        assert self.metadata is not None
        return self.metadata

    def fetch_direct_dependencies(self, slug: str, version: str) -> list[DependencySpec]:
        self.dependency_calls.append((slug, version))
        assert self.error is None
        return self.dependencies


def test_resolve_exact_skill_use_case_shapes_deterministic_result() -> None:
    request = ResolveRequestDto(slug="python.lint", version="1.2.3")
    registry_client = FakeRegistryClient(
        metadata=SkillMetadata(
            coordinate=SkillCoordinate(slug="python.lint", version="1.2.3"),
            name="Python Lint",
            description="Linting skill",
            tags=["python", "lint"],
            rendered_summary="Lint Python files consistently.",
            content_checksum_algorithm="sha256",
            content_checksum_digest="abc123",
            lifecycle_status="published",
            trust_tier="internal",
            published_at="2026-03-18T00:00:00Z",
        ),
        dependencies=[
            DependencySpec(slug="python.base", version="1.0.0", optional=False, markers=["linux"]),
            DependencySpec(slug="python.fs", version="2.1.0", optional=True, markers=[]),
        ],
    )

    result = ResolveExactSkillUseCase(registry_client).execute(request)

    assert registry_client.metadata_calls == [("python.lint", "1.2.3")]
    assert registry_client.dependency_calls == [("python.lint", "1.2.3")]
    assert result.requested_coordinate.slug == "python.lint"
    assert result.requested_coordinate.version == "1.2.3"
    assert result.selected_coordinate.slug == "python.lint"
    assert result.selected_coordinate.version == "1.2.3"
    assert result.skill.name == "Python Lint"
    assert result.skill.rendered_summary == "Lint Python files consistently."
    assert [dependency.slug for dependency in result.dependencies] == [
        "python.base",
        "python.fs",
    ]
    assert result.dependencies[1].optional is True
    assert result.status == "resolved"


def test_resolve_exact_skill_use_case_propagates_registry_errors() -> None:
    request = ResolveRequestDto(slug="missing.skill", version="9.9.9")
    registry_client = FakeRegistryClient(
        error=SkillNotFoundError("Skill version was not found."),
    )

    use_case = ResolveExactSkillUseCase(registry_client)

    try:
        use_case.execute(request)
    except SkillNotFoundError as exc:
        assert str(exc) == "Skill version was not found."
    else:
        raise AssertionError("Expected SkillNotFoundError to be propagated.")
