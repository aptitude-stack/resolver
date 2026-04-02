from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from aptitude_resolver.application import composition
from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    ExecutionPlanDto,
    ExecutionStepDto,
    InstalledSkillDto,
    InstallResultDto,
    LockedEdgeDto,
    LockedSkillDto,
    LockfileDto,
    LockRootDto,
    PolicyEvaluationDto,
    ResolvedGraphDto,
    ResolvedSkillNodeDto,
    ResolveCoordinateDto,
    ResolveQueryResultDto,
    ResolveSkillSummaryDto,
    SyncResultDto,
    TraceEntryDto,
)
from aptitude_resolver.domain.errors import (
    ContentChecksumMismatchError,
    InvalidResolverConfigurationError,
    InvalidLockfileError,
    SelectionSlugNotFoundError,
)
from aptitude_resolver.domain.models import (
    DiscoveryQuery,
    SkillCoordinate,
    VersionSummary,
)
from aptitude_resolver.interfaces.cli import app as app_module
from aptitude_resolver.telemetry.metrics import StageTiming


runner = CliRunner()


class QueueUseCase:
    def __init__(
        self, responses: list[object] | None = None, error: Exception | None = None
    ) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.requests: list[Any] = []

    def execute(self, request: Any) -> Any:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.responses
        return self.responses.pop(0)


def _resolved_result(
    *,
    slug: str = "python.lint",
    version: str = "1.2.3",
    selection_mode: str = "single_candidate",
) -> ResolveQueryResultDto:
    return ResolveQueryResultDto(
        requested_query="python lint",
        status="resolved",
        selection_mode=selection_mode,
        selected_coordinate=ResolveCoordinateDto(slug=slug, version=version),
        selected_skill=ResolveSkillSummaryDto(
            name="Python Lint" if slug == "python.lint" else "JavaScript Lint",
            description="Linting skill",
            tags=["lint"],
            runtime="python" if slug == "python.lint" else "javascript",
            rendered_summary="Lint files consistently.",
            lifecycle_status="published",
            trust_tier="internal",
        ),
        graph=ResolvedGraphDto(
            root=ResolveCoordinateDto(slug=slug, version=version),
            nodes=[
                ResolvedSkillNodeDto(
                    slug=slug,
                    version=version,
                    name="Python Lint" if slug == "python.lint" else "JavaScript Lint",
                    description="Linting skill",
                    tags=["lint"],
                    runtime="python" if slug == "python.lint" else "javascript",
                    rendered_summary="Lint files consistently.",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                )
            ],
            edges=[],
            install_order=[ResolveCoordinateDto(slug=slug, version=version)],
            conflicts=[],
        ),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="python lint",
                requested_version=None,
                selected_node_id=f"{slug}@{version}",
                selection_mode=selection_mode,
            ),
            nodes=[
                LockedSkillDto(
                    node_id=f"{slug}@{version}",
                    slug=slug,
                    version=version,
                    artifact_ref=f"/skills/{slug}/{version}/content",
                    name="Python Lint" if slug == "python.lint" else "JavaScript Lint",
                    description="Linting skill",
                    tags=["lint"],
                    headers={
                        "runtime": "python" if slug == "python.lint" else "javascript"
                    },
                    rendered_summary="Lint files consistently.",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": f"digest-{slug}-{version}",
                        "size_bytes": 256,
                    },
                )
            ],
            edges=[],
            install_order=[f"{slug}@{version}"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id=f"{slug}@{version}",
                    skill=slug,
                    version=version,
                    artifact_ref=f"/skills/{slug}/{version}/content",
                    action="materialize_local_skill",
                )
            ]
        ),
        trace=[
            TraceEntryDto(
                stage="selection",
                action="finalize_selection",
                message="Selected a skill.",
                data={"selection_mode": selection_mode},
            )
        ],
        policy_evaluations=[
            PolicyEvaluationDto(
                rule="allowed_lifecycle_status",
                passed=True,
                message="Lifecycle is allowed.",
                coordinate=ResolveCoordinateDto(slug=slug, version=version),
            )
        ],
    )


def _selection_required_result() -> ResolveQueryResultDto:
    return ResolveQueryResultDto(
        requested_query="lint",
        status="selection_required",
        candidates=[
            DiscoveryCandidateDto(
                slug="python.lint",
                version="1.2.3",
                name="Python Lint",
                description="Lint Python files",
                tags=["python", "lint"],
                labels=["python", "lint"],
                matched_labels=["python", "lint"],
                match_reasons=["exact_name_match"],
                runtime="python",
                lifecycle_status="published",
                trust_tier="internal",
                token_estimate=120,
                content_size_bytes=256,
                published_at="2026-03-18T00:00:00Z",
                ranking_position=1,
                selection_details=[
                    "tokens=120",
                    "size=256B",
                    "published=2026-03-18T00:00:00Z",
                ],
                selection_reason="ranked above js.lint@2.1.0: closer exact name match",
            ),
            DiscoveryCandidateDto(
                slug="js.lint",
                version="2.1.0",
                name="JavaScript Lint",
                description="Lint JavaScript files",
                tags=["javascript", "lint"],
                labels=["javascript", "lint"],
                matched_labels=["lint"],
                match_reasons=["label_overlap"],
                runtime="javascript",
                lifecycle_status="published",
                trust_tier="internal",
                token_estimate=250,
                content_size_bytes=320,
                published_at="2026-03-17T00:00:00Z",
                ranking_position=2,
                selection_details=[
                    "tokens=250",
                    "size=320B",
                    "published=2026-03-17T00:00:00Z",
                ],
            ),
        ],
        trace=[
            TraceEntryDto(
                stage="selection",
                action="await_user_choice",
                message="Multiple candidates remain.",
                data={},
            )
        ],
    )


def _installed_result(
    materialized_root: str = str(Path("skill_demo")),
) -> InstallResultDto:
    return InstallResultDto(
        requested_query="python lint",
        status="installed",
        selection_mode="single_candidate",
        selected_coordinate=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
        graph=ResolvedGraphDto(
            root=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            nodes=[],
            edges=[],
            install_order=[
                ResolveCoordinateDto(slug="dep.core", version="0.9.0"),
                ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            ],
            conflicts=[],
        ),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="python lint",
                requested_version=None,
                selected_node_id="python.lint@1.2.3",
                selection_mode="single_candidate",
            ),
            nodes=[
                LockedSkillDto(
                    node_id="dep.core@0.9.0",
                    slug="dep.core",
                    version="0.9.0",
                    artifact_ref="/skills/dep.core/0.9.0/content",
                    name="dep.core",
                    description="dep.core description",
                    tags=["core"],
                    headers={"runtime": "python"},
                    rendered_summary="dep.core summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-dep.core-0.9.0",
                        "size_bytes": 256,
                    },
                ),
                LockedSkillDto(
                    node_id="python.lint@1.2.3",
                    slug="python.lint",
                    version="1.2.3",
                    artifact_ref="/skills/python.lint/1.2.3/content",
                    name="python.lint",
                    description="python.lint description",
                    tags=["lint"],
                    headers={"runtime": "python"},
                    rendered_summary="python.lint summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-python.lint-1.2.3",
                        "size_bytes": 256,
                    },
                ),
            ],
            edges=[
                LockedEdgeDto(
                    source_node_id="python.lint@1.2.3",
                    target_node_id="dep.core@0.9.0",
                )
            ],
            install_order=["dep.core@0.9.0", "python.lint@1.2.3"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id="dep.core@0.9.0",
                    skill="dep.core",
                    version="0.9.0",
                    artifact_ref="/skills/dep.core/0.9.0/content",
                    action="materialize_local_skill",
                ),
                ExecutionStepDto(
                    node_id="python.lint@1.2.3",
                    skill="python.lint",
                    version="1.2.3",
                    artifact_ref="/skills/python.lint/1.2.3/content",
                    action="materialize_local_skill",
                ),
            ]
        ),
        installed_skills=[
            InstalledSkillDto(
                slug="dep.core",
                version="0.9.0",
                install_path=str(
                    Path(materialized_root) / "skills" / "dep.core" / "0.9.0"
                ),
            ),
            InstalledSkillDto(
                slug="python.lint",
                version="1.2.3",
                install_path=str(
                    Path(materialized_root) / "skills" / "python.lint" / "1.2.3"
                ),
            ),
        ],
        materialized_root=materialized_root,
        trace=[
            TraceEntryDto(
                stage="install",
                action="materialize_graph",
                message="Installed locally.",
                data={},
            )
        ],
    )


def _synced_result(
    lock_path: str, materialized_root: str = str(Path("skill_demo"))
) -> SyncResultDto:
    return SyncResultDto(
        lock_path=lock_path,
        requested_query="python lint",
        status="synced",
        selection_mode="single_candidate",
        selected_coordinate=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="python lint",
                requested_version=None,
                selected_node_id="python.lint@1.2.3",
                selection_mode="single_candidate",
            ),
            nodes=[
                LockedSkillDto(
                    node_id="dep.core@0.9.0",
                    slug="dep.core",
                    version="0.9.0",
                    artifact_ref="/skills/dep.core/0.9.0/content",
                    name="dep.core",
                    description="dep.core description",
                    tags=["core"],
                    headers={"runtime": "python"},
                    rendered_summary="dep.core summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-dep.core-0.9.0",
                        "size_bytes": 256,
                    },
                ),
                LockedSkillDto(
                    node_id="python.lint@1.2.3",
                    slug="python.lint",
                    version="1.2.3",
                    artifact_ref="/skills/python.lint/1.2.3/content",
                    name="python.lint",
                    description="python.lint description",
                    tags=["lint"],
                    headers={"runtime": "python"},
                    rendered_summary="python.lint summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-python.lint-1.2.3",
                        "size_bytes": 256,
                    },
                ),
            ],
            edges=[
                LockedEdgeDto(
                    source_node_id="python.lint@1.2.3",
                    target_node_id="dep.core@0.9.0",
                )
            ],
            install_order=["dep.core@0.9.0", "python.lint@1.2.3"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id="dep.core@0.9.0",
                    skill="dep.core",
                    version="0.9.0",
                    artifact_ref="/skills/dep.core/0.9.0/content",
                    action="materialize_local_skill",
                ),
                ExecutionStepDto(
                    node_id="python.lint@1.2.3",
                    skill="python.lint",
                    version="1.2.3",
                    artifact_ref="/skills/python.lint/1.2.3/content",
                    action="materialize_local_skill",
                ),
            ]
        ),
        installed_skills=[
            InstalledSkillDto(
                slug="dep.core",
                version="0.9.0",
                install_path=str(
                    Path(materialized_root) / "skills" / "dep.core" / "0.9.0"
                ),
            ),
            InstalledSkillDto(
                slug="python.lint",
                version="1.2.3",
                install_path=str(
                    Path(materialized_root) / "skills" / "python.lint" / "1.2.3"
                ),
            ),
        ],
        materialized_root=materialized_root,
        trace=[
            TraceEntryDto(
                stage="lockfile",
                action="load_lockfile",
                message=f"Loaded lockfile from {lock_path}.",
                data={"path": lock_path},
            )
        ],
    )


def test_cli_resolve_non_interactive_prints_stable_json(monkeypatch) -> None:
    use_case = QueueUseCase(
        responses=[_resolved_result(selection_mode="non_interactive_top_ranked")]
    )
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)

    def build_resolve_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_resolve_use_case", build_resolve_use_case)

    result = runner.invoke(app_module.app, ["resolve", "python lint"])

    assert result.exit_code == 0
    assert builder_kwargs == {}
    assert len(use_case.requests) == 1
    assert use_case.requests[0].interaction_mode is None
    assert use_case.requests[0].prompt_capable is False
    assert use_case.requests[0].select_slug is None
    assert close_calls == ["closed"]
    assert result.stdout == (
        _resolved_result(selection_mode="non_interactive_top_ranked").model_dump_json(
            indent=2, exclude_none=True
        )
        + "\n"
    )
    assert result.stderr == ""


def test_cli_resolve_interactive_prompts_and_replays_with_selected_slug(
    monkeypatch,
) -> None:
    use_case = QueueUseCase(
        responses=[
            _selection_required_result(),
            _resolved_result(
                slug="js.lint", version="2.1.0", selection_mode="interactive_choice"
            ),
        ]
    )
    close_calls: list[str] = []

    monkeypatch.setattr(app_module, "_is_interactive", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(app_module.app, ["resolve", "lint"], input="2\n")

    assert result.exit_code == 0
    assert "Multiple matching skills were found:" in result.stdout
    assert "tokens=120 | size=256B | published=2026-03-18T00:00:00Z" in result.stdout
    assert (
        "why ranked here: ranked above js.lint@2.1.0: closer exact name match"
        in result.stdout
    )
    assert len(use_case.requests) == 2
    assert use_case.requests[0].interaction_mode is None
    assert use_case.requests[0].prompt_capable is True
    assert use_case.requests[0].select_slug is None
    assert use_case.requests[1].interaction_mode == "never"
    assert use_case.requests[1].prompt_capable is False
    assert use_case.requests[1].select_slug == "js.lint"
    assert use_case.requests[1].selection_source == "interactive"
    assert close_calls == ["closed"]


def test_cli_resolve_select_slug_bypasses_prompt(monkeypatch) -> None:
    use_case = QueueUseCase(
        responses=[
            _resolved_result(
                slug="js.lint", version="2.1.0", selection_mode="explicit_slug"
            )
        ]
    )
    close_calls: list[str] = []

    monkeypatch.setattr(app_module, "_is_interactive", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app, ["resolve", "lint", "--select-slug", "js.lint"]
    )

    assert result.exit_code == 0
    assert len(use_case.requests) == 1
    assert use_case.requests[0].interaction_mode is None
    assert use_case.requests[0].prompt_capable is True
    assert use_case.requests[0].select_slug == "js.lint"
    assert close_calls == ["closed"]


def test_cli_install_prints_installed_result(monkeypatch, tmp_path) -> None:
    target = tmp_path / "skill_demo"
    use_case = QueueUseCase(responses=[_installed_result(str(target))])
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)

    def build_install_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_install_use_case", build_install_use_case)

    result = runner.invoke(
        app_module.app, ["install", "python lint", "--target", str(target)]
    )

    assert result.exit_code == 0
    assert builder_kwargs == {}
    assert len(use_case.requests) == 1
    assert use_case.requests[0].interaction_mode is None
    assert use_case.requests[0].prompt_capable is False
    assert use_case.requests[0].target == target
    assert close_calls == ["closed"]
    assert "Collecting python lint" in result.stdout
    assert "Installation Summary" in result.stdout
    assert "Using resolver candidate python.lint (1.2.3)" in result.stdout
    assert "Collecting dependency dep.core (0.9.0)" in result.stdout
    assert (
        "Installing collected resolver skills: dep.core, python.lint" in result.stdout
    )
    assert "Successfully installed dep.core-0.9.0 python.lint-1.2.3" in result.stdout
    assert f"Installed to: {target}" in result.stdout


def test_cli_install_prints_pipe_separated_telemetry_when_interactive(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "skill_demo"
    use_case = QueueUseCase(responses=[_installed_result(str(target))])

    @contextmanager
    def capture_install_telemetry():
        yield [
            StageTiming(stage="discovery", duration_ms=95.679),
            StageTiming(stage="materialization", duration_ms=18.2),
        ]

    monkeypatch.setattr(app_module, "_is_interactive", lambda: True)
    monkeypatch.setattr(app_module, "capture_cli_telemetry", capture_install_telemetry)
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda **_kwargs: (use_case, lambda: None),
    )

    result = runner.invoke(
        app_module.app,
        [
            "install",
            "python lint",
            "--target",
            str(target),
            "--interaction-mode",
            "never",
        ],
    )

    assert result.exit_code == 0
    assert (
        "Install telemetry | Discovery 95.7ms | Materialization 18.2ms" in result.stdout
    )
    assert (
        "Install telemetry | Discovery 95.7ms | Materialization 18.2ms"
        not in result.stderr
    )


def test_cli_install_json_flag_preserves_structured_output(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "skill_demo"
    installed_result = _installed_result(str(target))
    use_case = QueueUseCase(responses=[installed_result])
    close_calls: list[str] = []

    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app,
        ["install", "python lint", "--target", str(target), "--json"],
    )

    assert result.exit_code == 0
    assert close_calls == ["closed"]
    assert result.stdout == (
        installed_result.model_dump_json(indent=2, exclude_none=True) + "\n"
    )


def test_cli_install_passes_selection_flag_overrides_to_builder(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "skill_demo"
    use_case = QueueUseCase(responses=[_installed_result(str(target))])
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)

    def build_install_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_install_use_case", build_install_use_case)

    result = runner.invoke(
        app_module.app,
        [
            "install",
            "python lint",
            "--target",
            str(target),
            "--prefer",
            "low-cost",
            "--interaction-mode",
            "never",
            "--allow-trust",
            "verified,internal",
            "--allow-lifecycle",
            "published,deprecated",
            "--max-tokens",
            "500",
            "--max-content-size",
            "2048",
        ],
    )

    assert result.exit_code == 0
    assert builder_kwargs == {
        "selection_profile_override": "low-cost",
        "interaction_mode_override": "never",
        "allowed_trust_tiers_override": ["verified", "internal"],
        "allowed_lifecycle_statuses_override": ["published", "deprecated"],
        "max_token_estimate_override": 500,
        "max_content_size_bytes_override": 2048,
    }
    assert use_case.requests[0].interaction_mode is None
    assert close_calls == ["closed"]


def test_cli_install_reports_missing_environment_variables_cleanly(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)
    monkeypatch.setattr(
        app_module, "build_install_use_case", composition.build_install_use_case
    )
    monkeypatch.delenv("APTITUDE_SERVER_BASE_URL", raising=False)
    monkeypatch.delenv("APTITUDE_READ_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app_module.app, ["install", "python lint"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Aptitude is not configured." in result.stderr
    assert "APTITUDE_SERVER_BASE_URL" in result.stderr
    assert "APTITUDE_READ_TOKEN" in result.stderr
    assert ".env" in result.stderr
    assert "InvalidResolverConfigurationError" not in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_resolve_passes_policy_flag_overrides_to_builder(monkeypatch) -> None:
    use_case = QueueUseCase(
        responses=[_resolved_result(selection_mode="non_interactive_top_ranked")]
    )
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)

    def build_resolve_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_resolve_use_case", build_resolve_use_case)

    result = runner.invoke(
        app_module.app,
        [
            "resolve",
            "python lint",
            "--allow-trust",
            "verified",
            "--allow-lifecycle",
            "published",
            "--max-tokens",
            "250",
            "--max-content-size",
            "512",
        ],
    )

    assert result.exit_code == 0
    assert builder_kwargs == {
        "allowed_trust_tiers_override": ["verified"],
        "allowed_lifecycle_statuses_override": ["published"],
        "max_token_estimate_override": 250,
        "max_content_size_bytes_override": 512,
    }
    assert close_calls == ["closed"]


def test_cli_resolve_prints_structured_error_for_invalid_policy_override(
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)
    close_calls: list[str] = []

    def build_resolve_use_case(**kwargs):
        raise InvalidResolverConfigurationError(
            "CLI override", "allowed_trust_tiers contains unknown values: unknown-tier."
        )

    monkeypatch.setattr(app_module, "build_resolve_use_case", build_resolve_use_case)

    result = runner.invoke(
        app_module.app,
        ["resolve", "python lint", "--allow-trust", "unknown-tier"],
    )

    assert result.exit_code == 1
    assert close_calls == []
    assert "Invalid CLI configuration." in result.stderr
    assert "allowed_trust_tiers contains unknown values: unknown-tier." in result.stderr


def test_cli_resolve_policy_override_can_reject_candidates_end_to_end(
    monkeypatch,
) -> None:
    class FakeSettings:
        pass

    class FakeRegistryClient:
        def __init__(self, settings) -> None:
            self.settings = settings

        def close(self) -> None:
            pass

        def discover_candidate_slugs(self, query: DiscoveryQuery) -> list[str]:
            return ["python.lint"]

        def fetch_skill_identity(self, slug: str):
            raise AssertionError(
                "slug identity lookup should not be used for this query"
            )

        def list_skill_versions(self, slug: str) -> list[VersionSummary]:
            return [
                VersionSummary(
                    coordinate=SkillCoordinate(slug="python.lint", version="1.2.3"),
                    name="Python Lint",
                    description="Lint Python files.",
                    tags=["python", "lint"],
                    headers={"runtime": "python"},
                    rendered_summary="Lint Python files.",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-28T00:00:00Z",
                    content_checksum_algorithm="sha256",
                    content_checksum_digest="digest-python.lint-1.2.3",
                    content_size_bytes=256,
                    token_estimate=100,
                    maturity_score=0.9,
                    security_score=0.95,
                )
            ]

        def fetch_skill_metadata(self, slug: str, version: str):
            raise AssertionError(
                "metadata lookup should not happen after candidate policy rejection"
            )

        def fetch_direct_dependencies(self, slug: str, version: str) -> list[object]:
            return []

    monkeypatch.setattr(composition, "Settings", FakeSettings)
    monkeypatch.setattr(composition, "RegistryClient", FakeRegistryClient)
    monkeypatch.setattr(
        composition, "load_workspace_aptitude_config", lambda cwd=None: None
    )
    monkeypatch.setattr(composition, "load_user_aptitude_config", lambda: None)
    monkeypatch.setattr(
        composition, "read_env_selection_overrides", lambda env=None: None
    )
    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)
    monkeypatch.setattr(
        app_module, "build_resolve_use_case", composition.build_resolve_use_case
    )

    result = runner.invoke(
        app_module.app,
        ["resolve", "python lint", "--allow-trust", "verified"],
    )

    assert result.exit_code == 1
    assert "Policy rejected the requested operation." in result.stderr
    assert "All discovered candidates were rejected by policy." in result.stderr


def test_cli_sync_prints_synced_result(monkeypatch, tmp_path) -> None:
    lock_path = tmp_path / "aptitude.lock.json"
    target = tmp_path / "skill_demo"
    synced_result = _synced_result(str(lock_path.resolve()), str(target))
    use_case = QueueUseCase(responses=[synced_result])
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_sync_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app,
        ["sync", "--lock", str(lock_path), "--target", str(target)],
    )

    assert result.exit_code == 0
    assert len(use_case.requests) == 1
    assert use_case.requests[0].lock_path == lock_path
    assert use_case.requests[0].target == target
    assert close_calls == ["closed"]
    assert f"Syncing locked resolver skills from {lock_path.resolve()}" in result.stdout
    assert "Installing locked resolver skills: dep.core, python.lint" in result.stdout
    assert "Successfully synced dep.core-0.9.0 python.lint-1.2.3" in result.stdout
    assert f"Installed to: {target}" in result.stdout


def test_cli_sync_json_flag_preserves_structured_output(monkeypatch, tmp_path) -> None:
    lock_path = tmp_path / "aptitude.lock.json"
    target = tmp_path / "skill_demo"
    synced_result = _synced_result(str(lock_path.resolve()), str(target))
    use_case = QueueUseCase(responses=[synced_result])
    close_calls: list[str] = []

    monkeypatch.setattr(
        app_module,
        "build_sync_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app,
        ["sync", "--lock", str(lock_path), "--target", str(target), "--json"],
    )

    assert result.exit_code == 0
    assert close_calls == ["closed"]
    assert result.stdout == (
        synced_result.model_dump_json(indent=2, exclude_none=True) + "\n"
    )


def test_cli_sync_prints_structured_error_for_missing_lockfile(
    monkeypatch, tmp_path
) -> None:
    close_calls: list[str] = []
    missing_lock = tmp_path / "missing.lock.json"

    monkeypatch.setattr(
        app_module,
        "build_sync_use_case",
        lambda: (
            QueueUseCase(
                error=InvalidLockfileError(
                    f"Lockfile not found: {missing_lock.resolve()}"
                )
            ),
            lambda: close_calls.append("closed"),
        ),
    )

    result = runner.invoke(app_module.app, ["sync", "--lock", str(missing_lock)])

    assert result.exit_code == 1
    assert close_calls == ["closed"]
    assert "Lockfile error." in result.stderr
    assert "Lockfile not found:" in result.stderr


def test_cli_install_without_query_launches_install_wizard_flow(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        app_module,
        "run_cli_wizard",
        lambda **kwargs: calls.append(kwargs),
    )

    result = runner.invoke(app_module.app, ["install"])

    assert result.exit_code == 0
    assert calls == [{"initial_flow": "install", "target": Path("skill_demo")}]


def test_cli_install_with_only_query_launches_wizard_at_plan_step(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(app_module, "_is_interactive", lambda: True)

    monkeypatch.setattr(
        app_module,
        "run_cli_wizard",
        lambda **kwargs: calls.append(kwargs),
    )

    result = runner.invoke(app_module.app, ["install", "python lint"])

    assert result.exit_code == 0
    assert calls == [
        {
            "initial_flow": "install",
            "initial_query": "python lint",
            "target": Path("skill_demo"),
        }
    ]


def test_cli_sync_without_lock_launches_sync_wizard_flow(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        app_module,
        "run_cli_wizard",
        lambda **kwargs: calls.append(kwargs),
    )

    result = runner.invoke(app_module.app, ["sync"])

    assert result.exit_code == 0
    assert calls == [{"initial_flow": "sync", "target": Path("skill_demo")}]


def test_cli_sync_with_json_still_requires_lock_option() -> None:
    result = runner.invoke(app_module.app, ["sync", "--json"])

    assert result.exit_code == 2
    assert "Missing option '--lock'" in result.stderr


def test_cli_sync_renders_unexpected_errors_without_tracebacks(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_sync_use_case",
        lambda: (_ for _ in ()).throw(RuntimeError("unable to open database file")),
    )

    result = runner.invoke(app_module.app, ["sync", "--lock", "aptitude.lock.json"])

    assert result.exit_code == 1
    assert "Aptitude could not open its local cache." in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_resolve_prints_structured_error(monkeypatch) -> None:
    close_calls: list[str] = []

    monkeypatch.setattr(app_module, "_is_interactive", lambda: False)
    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda: (
            QueueUseCase(
                error=SelectionSlugNotFoundError(
                    "lint", "missing.skill", ["python.lint"]
                )
            ),
            lambda: close_calls.append("closed"),
        ),
    )

    result = runner.invoke(
        app_module.app, ["resolve", "lint", "--select-slug", "missing.skill"]
    )

    assert result.exit_code == 1
    assert close_calls == ["closed"]
    assert "Requested selection is not available." in result.stderr
    assert "Selected slug: missing.skill" in result.stderr
    assert result.stdout == ""


def test_format_error_renders_environment_configuration_errors_for_humans() -> None:
    rendered = app_module._format_error(
        InvalidResolverConfigurationError(
            "environment",
            "Missing required environment variables: "
            "APTITUDE_SERVER_BASE_URL, APTITUDE_READ_TOKEN.",
        )
    )

    assert "Aptitude is not configured." in rendered
    assert "APTITUDE_SERVER_BASE_URL" in rendered
    assert "APTITUDE_READ_TOKEN" in rendered
    assert ".env" in rendered
    assert "InvalidResolverConfigurationError" not in rendered


def test_format_error_keeps_structured_payload_for_non_environment_config_errors() -> (
    None
):
    rendered = app_module._format_error(
        InvalidResolverConfigurationError(
            "CLI override", "unsupported interaction mode"
        )
    )

    assert "Invalid CLI configuration." in rendered
    assert "unsupported interaction mode" in rendered
    assert "Review the supplied flags and try again." in rendered


def test_format_error_includes_checksum_error_payload_details() -> None:
    rendered = app_module._format_error(
        ContentChecksumMismatchError(
            slug="python.lint",
            version="1.2.3",
            algorithm="sha256",
            expected_digest="expected",
            actual_digest="actual",
        )
    )

    assert "Downloaded content failed integrity verification." in rendered
    assert "Skill: python.lint@1.2.3" in rendered
    assert "Expected digest: expected" in rendered
    assert "Actual digest: actual" in rendered
