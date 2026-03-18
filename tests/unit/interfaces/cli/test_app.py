from __future__ import annotations

from typer.testing import CliRunner

from aptitude_client.application.dto import (
    ResolveCoordinateDto,
    ResolveDependencyDto,
    ResolveResultDto,
    ResolveSkillSummaryDto,
)
from aptitude_client.domain.errors import (
    DiscoveryAmbiguousMatchError,
    InvalidCoordinateError,
    SkillNotFoundError,
    VersionSelectionUnavailableError,
)
from aptitude_client.interfaces.cli import app as app_module


runner = CliRunner()


class FakeUseCase:
    def __init__(self, result: ResolveResultDto | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.requests: list[tuple[str, str | None]] = []

    def execute(self, request) -> ResolveResultDto:
        self.requests.append((request.query, request.version))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def test_cli_resolve_happy_path_prints_stable_json(monkeypatch) -> None:
    use_case = FakeUseCase(
        result=ResolveResultDto(
            requested_coordinate=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            selected_coordinate=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            skill=ResolveSkillSummaryDto(
                name="Python Lint",
                description="Linting skill",
                tags=["python", "lint"],
                rendered_summary="Lint Python files consistently.",
                lifecycle_status="published",
                trust_tier="internal",
            ),
            dependencies=[
                ResolveDependencyDto(
                    slug="python.base",
                    version="1.0.0",
                    optional=False,
                    markers=["linux"],
                )
            ],
            status="resolved",
        )
    )
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app,
        ["resolve", "python.lint", "--version", "1.2.3"],
    )

    assert result.exit_code == 0
    assert use_case.requests == [("python.lint", "1.2.3")]
    assert close_calls == ["closed"]
    assert result.stdout == (use_case.result.model_dump_json(indent=2, exclude_none=True) + "\n")
    assert result.stderr == ""


def test_cli_resolve_discovery_query_prints_requested_query(monkeypatch) -> None:
    use_case = FakeUseCase(
        result=ResolveResultDto(
            requested_query="Python Lint",
            resolution_strategy="discovery",
            requested_coordinate=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            selected_coordinate=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            skill=ResolveSkillSummaryDto(
                name="Python Lint",
                description="Linting skill",
                tags=["python", "lint"],
                rendered_summary="Lint Python files consistently.",
                lifecycle_status="published",
                trust_tier="internal",
            ),
            dependencies=[],
            status="resolved",
        )
    )
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app,
        ["resolve", "Python Lint", "--version", "1.2.3"],
    )

    assert result.exit_code == 0
    assert use_case.requests == [("Python Lint", "1.2.3")]
    assert close_calls == ["closed"]
    assert '"requested_query": "Python Lint"' in result.stdout
    assert '"resolution_strategy": "discovery"' in result.stdout


def test_cli_resolve_skill_not_found_prints_structured_error(monkeypatch) -> None:
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (
            FakeUseCase(error=SkillNotFoundError("Skill version was not found.")),
            lambda: close_calls.append("closed"),
        ),
    )

    result = runner.invoke(
        app_module.app,
        ["resolve", "missing.skill", "--version", "9.9.9"],
    )

    assert result.exit_code == 1
    assert close_calls == ["closed"]
    assert result.stdout == ""
    assert result.stderr == (
        '{\n'
        '  "error": {\n'
        '    "type": "SkillNotFoundError",\n'
        '    "message": "Skill version was not found."\n'
        "  }\n"
        "}\n"
    )


def test_cli_resolve_invalid_coordinate_prints_structured_error(monkeypatch) -> None:
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (
            FakeUseCase(error=InvalidCoordinateError("Version must be valid semver.")),
            lambda: close_calls.append("closed"),
        ),
    )

    result = runner.invoke(
        app_module.app,
        ["resolve", "python.lint", "--version", "not-a-semver"],
    )

    assert result.exit_code == 1
    assert close_calls == ["closed"]
    assert result.stdout == ""
    assert result.stderr == (
        '{\n'
        '  "error": {\n'
        '    "type": "InvalidCoordinateError",\n'
        '    "message": "Version must be valid semver."\n'
        "  }\n"
        "}\n"
    )


def test_cli_resolve_without_version_prints_runtime_limit_error(monkeypatch) -> None:
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (
            FakeUseCase(error=VersionSelectionUnavailableError("Python Lint")),
            lambda: close_calls.append("closed"),
        ),
    )

    result = runner.invoke(
        app_module.app,
        ["resolve", "Python Lint"],
    )

    assert result.exit_code == 1
    assert close_calls == ["closed"]
    assert '"type": "VersionSelectionUnavailableError"' in result.stderr
    assert '"query": "Python Lint"' in result.stderr


def test_cli_resolve_ambiguous_discovery_prints_candidates(monkeypatch) -> None:
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (
            FakeUseCase(
                error=DiscoveryAmbiguousMatchError("lint", ["python.lint", "js.lint"])
            ),
            lambda: close_calls.append("closed"),
        ),
    )

    result = runner.invoke(
        app_module.app,
        ["resolve", "lint", "--version", "1.2.3"],
    )

    assert result.exit_code == 1
    assert close_calls == ["closed"]
    assert '"type": "DiscoveryAmbiguousMatchError"' in result.stderr
    assert '"candidates": [' in result.stderr
    assert '"js.lint"' in result.stderr
    assert '"python.lint"' in result.stderr
