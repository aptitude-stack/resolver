from __future__ import annotations

from contextlib import contextmanager
from io import StringIO
from pathlib import Path
import re
from typing import Any

import pytest
from rich.console import Console
from typer.testing import CliRunner

from aptitude_resolver.application import composition
from aptitude_resolver.application.dto import (
    ConfigLayerDto,
    DiscoveryCandidateDto,
    EffectivePolicyReportDto,
    ExportedSkillDto,
    ExecutionPlanDto,
    InspectSkillResultDto,
    InspectSkillSummaryDto,
    InspectVersionDto,
    ExecutionStepDto,
    InstalledSkillDto,
    InstallResultDto,
    LockedEdgeDto,
    LockedSkillDto,
    LockfileDto,
    LockRootDto,
    PolicyEvaluationDto,
    PolicyConfigSnapshotDto,
    PolicyMergeSemanticsDto,
    ResolvedGraphDto,
    ResolvedSkillNodeDto,
    ResolveCoordinateDto,
    ResolveQueryResultDto,
    ResolveSkillSummaryDto,
    SelectionConfigSnapshotDto,
    SearchSkillsResultDto,
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
from aptitude_resolver.interfaces.cli import wizard as wizard_module
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
    slug: str = "python-lint",
    version: str = "1.2.3",
    selection_mode: str = "single_candidate",
) -> ResolveQueryResultDto:
    return ResolveQueryResultDto(
        requested_query="python lint",
        status="resolved",
        selection_mode=selection_mode,
        selected_coordinate=ResolveCoordinateDto(slug=slug, version=version),
        selected_skill=ResolveSkillSummaryDto(
            name="Python Lint" if slug == "python-lint" else "JavaScript Lint",
            description="Linting skill",
            tags=["lint"],
            runtime="python" if slug == "python-lint" else "javascript",
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
                    name="Python Lint" if slug == "python-lint" else "JavaScript Lint",
                    description="Linting skill",
                    tags=["lint"],
                    runtime="python" if slug == "python-lint" else "javascript",
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
                    name="Python Lint" if slug == "python-lint" else "JavaScript Lint",
                    description="Linting skill",
                    tags=["lint"],
                    headers={
                        "runtime": "python" if slug == "python-lint" else "javascript"
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
                slug="python-lint",
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
                selection_reason="ranked above js-lint@2.1.0: closer exact name match",
            ),
            DiscoveryCandidateDto(
                slug="js-lint",
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


def _search_result() -> SearchSkillsResultDto:
    return SearchSkillsResultDto(
        requested_query="python lint",
        status="found",
        candidates=[
            DiscoveryCandidateDto(
                slug="python-lint",
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
            )
        ],
    )


def _inspect_selection_required_result() -> InspectSkillResultDto:
    return InspectSkillResultDto(
        requested_query="lint",
        status="selection_required",
        candidates=[
            DiscoveryCandidateDto(
                slug="python-lint",
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
            ),
            DiscoveryCandidateDto(
                slug="js-lint",
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
            ),
        ],
    )


def _inspect_result(
    *,
    slug: str = "python-lint",
    version: str = "1.2.3",
    selection_mode: str = "single_candidate",
) -> InspectSkillResultDto:
    return InspectSkillResultDto(
        requested_query="python lint",
        status="inspected",
        selection_mode=selection_mode,
        selected_coordinate=ResolveCoordinateDto(slug=slug, version=version),
        skill=InspectSkillSummaryDto(
            name="Python Lint",
            description="Lint Python files",
            tags=["python", "lint"],
            runtime="python",
            rendered_summary="Lint files consistently.",
            lifecycle_status="published",
            trust_tier="internal",
            published_at="2026-03-18T00:00:00Z",
            token_estimate=120,
            content_size_bytes=256,
            maturity_score=0.9,
            security_score=0.95,
            content_checksum_algorithm="sha256",
            content_checksum_digest=f"digest-{slug}-{version}",
            headers={"runtime": "python"},
        ),
        available_versions=[
            InspectVersionDto(
                version=version,
                lifecycle_status="published",
                trust_tier="internal",
                published_at="2026-03-18T00:00:00Z",
                is_current_default=True,
                token_estimate=120,
                content_size_bytes=256,
                rendered_summary="Lint files consistently.",
            )
        ],
        content_preview="# Python Lint\n\nUse this skill.",
        content_preview_truncated=False,
    )


def _installed_result(
    materialized_root: str = str(Path("aptitude_state")),
    export_root: str = str(Path(".codex") / "skills"),
) -> InstallResultDto:
    return InstallResultDto(
        requested_query="python lint",
        status="installed",
        selection_mode="single_candidate",
        selected_coordinate=ResolveCoordinateDto(slug="python-lint", version="1.2.3"),
        graph=ResolvedGraphDto(
            root=ResolveCoordinateDto(slug="python-lint", version="1.2.3"),
            nodes=[],
            edges=[],
            install_order=[
                ResolveCoordinateDto(slug="dep-core", version="0.9.0"),
                ResolveCoordinateDto(slug="python-lint", version="1.2.3"),
            ],
            conflicts=[],
        ),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="python lint",
                requested_version=None,
                selected_node_id="python-lint@1.2.3",
                selection_mode="single_candidate",
            ),
            nodes=[
                LockedSkillDto(
                    node_id="dep-core@0.9.0",
                    slug="dep-core",
                    version="0.9.0",
                    artifact_ref="/skills/dep-core/0.9.0/content",
                    name="dep-core",
                    description="dep-core description",
                    tags=["core"],
                    headers={"runtime": "python"},
                    rendered_summary="dep-core summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-dep-core-0.9.0",
                        "size_bytes": 256,
                    },
                ),
                LockedSkillDto(
                    node_id="python-lint@1.2.3",
                    slug="python-lint",
                    version="1.2.3",
                    artifact_ref="/skills/python-lint/1.2.3/content",
                    name="python-lint",
                    description="python-lint description",
                    tags=["lint"],
                    headers={"runtime": "python"},
                    rendered_summary="python-lint summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-python-lint-1.2.3",
                        "size_bytes": 256,
                    },
                ),
            ],
            edges=[
                LockedEdgeDto(
                    source_node_id="python-lint@1.2.3",
                    target_node_id="dep-core@0.9.0",
                )
            ],
            install_order=["dep-core@0.9.0", "python-lint@1.2.3"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id="dep-core@0.9.0",
                    skill="dep-core",
                    version="0.9.0",
                    artifact_ref="/skills/dep-core/0.9.0/content",
                    action="materialize_local_skill",
                ),
                ExecutionStepDto(
                    node_id="python-lint@1.2.3",
                    skill="python-lint",
                    version="1.2.3",
                    artifact_ref="/skills/python-lint/1.2.3/content",
                    action="materialize_local_skill",
                ),
            ]
        ),
        installed_skills=[
            InstalledSkillDto(
                slug="dep-core",
                version="0.9.0",
                install_path=str(
                    Path(materialized_root) / "skills" / "dep-core" / "0.9.0"
                ),
            ),
            InstalledSkillDto(
                slug="python-lint",
                version="1.2.3",
                install_path=str(
                    Path(materialized_root) / "skills" / "python-lint" / "1.2.3"
                ),
            ),
        ],
        exported_skills=[
            ExportedSkillDto(
                agent="codex",
                scope="project",
                slug="dep-core",
                version="0.9.0",
                destination_path=str(Path(export_root) / "dep-core"),
                skill_markdown_path=str(Path(export_root) / "dep-core" / "SKILL.md"),
                metadata_path=str(
                    Path(export_root) / "dep-core" / ".aptitude-export.json"
                ),
            ),
            ExportedSkillDto(
                agent="codex",
                scope="project",
                slug="python-lint",
                version="1.2.3",
                destination_path=str(Path(export_root) / "python-lint"),
                skill_markdown_path=str(Path(export_root) / "python-lint" / "SKILL.md"),
                metadata_path=str(
                    Path(export_root) / "python-lint" / ".aptitude-export.json"
                ),
            ),
        ],
        materialized_root=materialized_root,
        lock_path=str(Path("aptitude.lock.json")),
        export_roots={"codex": export_root},
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
    lock_path: str, materialized_root: str = str(Path("aptitude_state"))
) -> SyncResultDto:
    return SyncResultDto(
        lock_path=lock_path,
        requested_query="python lint",
        status="synced",
        selection_mode="single_candidate",
        selected_coordinate=ResolveCoordinateDto(slug="python-lint", version="1.2.3"),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="python lint",
                requested_version=None,
                selected_node_id="python-lint@1.2.3",
                selection_mode="single_candidate",
            ),
            nodes=[
                LockedSkillDto(
                    node_id="dep-core@0.9.0",
                    slug="dep-core",
                    version="0.9.0",
                    artifact_ref="/skills/dep-core/0.9.0/content",
                    name="dep-core",
                    description="dep-core description",
                    tags=["core"],
                    headers={"runtime": "python"},
                    rendered_summary="dep-core summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-dep-core-0.9.0",
                        "size_bytes": 256,
                    },
                ),
                LockedSkillDto(
                    node_id="python-lint@1.2.3",
                    slug="python-lint",
                    version="1.2.3",
                    artifact_ref="/skills/python-lint/1.2.3/content",
                    name="python-lint",
                    description="python-lint description",
                    tags=["lint"],
                    headers={"runtime": "python"},
                    rendered_summary="python-lint summary",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": "digest-python-lint-1.2.3",
                        "size_bytes": 256,
                    },
                ),
            ],
            edges=[
                LockedEdgeDto(
                    source_node_id="python-lint@1.2.3",
                    target_node_id="dep-core@0.9.0",
                )
            ],
            install_order=["dep-core@0.9.0", "python-lint@1.2.3"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id="dep-core@0.9.0",
                    skill="dep-core",
                    version="0.9.0",
                    artifact_ref="/skills/dep-core/0.9.0/content",
                    action="materialize_local_skill",
                ),
                ExecutionStepDto(
                    node_id="python-lint@1.2.3",
                    skill="python-lint",
                    version="1.2.3",
                    artifact_ref="/skills/python-lint/1.2.3/content",
                    action="materialize_local_skill",
                ),
            ]
        ),
        installed_skills=[
            InstalledSkillDto(
                slug="dep-core",
                version="0.9.0",
                install_path=str(
                    Path(materialized_root) / "skills" / "dep-core" / "0.9.0"
                ),
            ),
            InstalledSkillDto(
                slug="python-lint",
                version="1.2.3",
                install_path=str(
                    Path(materialized_root) / "skills" / "python-lint" / "1.2.3"
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


def test_cli_search_prints_ranked_candidates(monkeypatch) -> None:
    use_case = QueueUseCase(responses=[_search_result()])
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: False)

    def build_search_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_search_use_case", build_search_use_case)

    result = runner.invoke(app_module.app, ["search", "python lint"])

    assert result.exit_code == 0
    assert builder_kwargs == {
        "selection_profile_override": None,
        "interaction_mode_override": None,
        "allowed_trust_tiers_override": None,
        "allowed_lifecycle_statuses_override": None,
        "max_token_estimate_override": None,
        "max_content_size_bytes_override": None,
        "cwd": Path.cwd(),
    }
    assert len(use_case.requests) == 1
    assert use_case.requests[0].query == "python lint"
    assert close_calls == ["closed"]
    assert "Search Results" in result.stdout
    assert "python-lint@1.2.3 - Python Lint" in result.stdout
    assert 'aptitude inspect "python lint" --select-slug SLUG' in result.stdout


def test_cli_search_interactive_uses_rich_panels(monkeypatch) -> None:
    use_case = QueueUseCase(responses=[_search_result()])

    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_search_use_case",
        lambda **_kwargs: (use_case, lambda: None),
    )

    result = runner.invoke(app_module.app, ["search", "python lint"])

    assert result.exit_code == 0
    assert "Search Summary" in result.stdout
    assert "Ranked Candidates" in result.stdout
    assert "Next Steps" in result.stdout
    assert "python-lint" in result.stdout
    assert "aptitude install SLUG" in result.stdout


def test_cli_search_json_outputs_structured_result(monkeypatch) -> None:
    search_result = _search_result()
    use_case = QueueUseCase(responses=[search_result])

    monkeypatch.setattr(
        app_module,
        "build_search_use_case",
        lambda **_kwargs: (use_case, lambda: None),
    )

    result = runner.invoke(app_module.app, ["search", "python lint", "--json"])

    assert result.exit_code == 0
    assert result.stdout == (
        search_result.model_dump_json(indent=2, exclude_none=True) + "\n"
    )


def test_cli_search_passes_policy_flag_overrides_to_builder(monkeypatch) -> None:
    use_case = QueueUseCase(responses=[_search_result()])
    builder_kwargs: dict[str, object] = {}

    def build_search_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: None

    monkeypatch.setattr(app_module, "build_search_use_case", build_search_use_case)

    result = runner.invoke(
        app_module.app,
        [
            "search",
            "python lint",
            "--prefer",
            "high-trust",
            "--allow-trust",
            "verified,internal",
            "--allow-lifecycle",
            "published",
            "--max-tokens",
            "500",
            "--max-content-size",
            "2048",
        ],
    )

    assert result.exit_code == 0
    assert builder_kwargs == {
        "selection_profile_override": "high-trust",
        "interaction_mode_override": None,
        "allowed_trust_tiers_override": ["verified", "internal"],
        "allowed_lifecycle_statuses_override": ["published"],
        "max_token_estimate_override": 500,
        "max_content_size_bytes_override": 2048,
        "cwd": Path.cwd(),
    }


def test_cli_inspect_prints_skill_metadata_and_preview(monkeypatch) -> None:
    use_case = QueueUseCase(responses=[_inspect_result()])
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)

    def build_inspect_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_inspect_use_case", build_inspect_use_case)

    result = runner.invoke(app_module.app, ["inspect", "python lint"])

    assert result.exit_code == 0
    assert len(use_case.requests) == 1
    assert use_case.requests[0].query == "python lint"
    assert use_case.requests[0].prompt_capable is False
    assert use_case.requests[0].preview_char_limit == 4000
    assert builder_kwargs["cwd"] == Path.cwd()
    assert close_calls == ["closed"]
    assert "Skill Inspection" in result.stdout
    assert "Selected: python-lint@1.2.3" in result.stdout
    assert "Checksum: sha256:digest-python-lint-1.2.3" in result.stdout
    assert "# Python Lint" in result.stdout


def test_cli_inspect_interactive_uses_rich_panels(monkeypatch) -> None:
    use_case = QueueUseCase(responses=[_inspect_result()])

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_inspect_use_case",
        lambda **_kwargs: (use_case, lambda: None),
    )

    result = runner.invoke(app_module.app, ["inspect", "python lint"])

    assert result.exit_code == 0
    assert "Skill Inspection" in result.stdout
    assert "Metadata" in result.stdout
    assert "Available Versions" in result.stdout
    assert "Markdown Preview" in result.stdout
    assert "python-lint (1.2.3)" in result.stdout


def test_cli_inspect_interactive_prompts_and_replays_with_selected_slug(
    monkeypatch,
) -> None:
    use_case = QueueUseCase(
        responses=[
            _inspect_selection_required_result(),
            _inspect_result(
                slug="js-lint", version="2.1.0", selection_mode="interactive_choice"
            ),
        ]
    )

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_inspect_use_case",
        lambda **_kwargs: (use_case, lambda: None),
    )

    result = runner.invoke(app_module.app, ["inspect", "lint"], input="2\n")

    assert result.exit_code == 0
    assert "Multiple matching skills were found:" in result.stdout
    assert len(use_case.requests) == 2
    assert use_case.requests[0].prompt_capable is True
    assert use_case.requests[0].select_slug is None
    assert use_case.requests[1].interaction_mode == "never"
    assert use_case.requests[1].prompt_capable is False
    assert use_case.requests[1].select_slug == "js-lint"
    assert use_case.requests[1].selection_source == "interactive"


def test_cli_inspect_json_outputs_structured_result(monkeypatch) -> None:
    inspect_result = _inspect_result()
    use_case = QueueUseCase(responses=[inspect_result])

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_inspect_use_case",
        lambda **_kwargs: (use_case, lambda: None),
    )

    result = runner.invoke(
        app_module.app,
        ["inspect", "python lint", "--preview-chars", "1200", "--json"],
    )

    assert result.exit_code == 0
    assert use_case.requests[0].prompt_capable is False
    assert use_case.requests[0].preview_char_limit == 1200
    assert result.stdout == (
        inspect_result.model_dump_json(indent=2, exclude_none=True) + "\n"
    )


def test_cli_inspect_passes_selection_flag_overrides_to_builder(monkeypatch) -> None:
    use_case = QueueUseCase(responses=[_inspect_result()])
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)

    def build_inspect_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: None

    monkeypatch.setattr(app_module, "build_inspect_use_case", build_inspect_use_case)

    result = runner.invoke(
        app_module.app,
        [
            "inspect",
            "python lint",
            "--version",
            "1.2.3",
            "--select-slug",
            "python-lint",
            "--prefer",
            "low-cost",
            "--interaction-mode",
            "never",
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
        "selection_profile_override": "low-cost",
        "interaction_mode_override": "never",
        "allowed_trust_tiers_override": ["verified"],
        "allowed_lifecycle_statuses_override": ["published"],
        "max_token_estimate_override": 250,
        "max_content_size_bytes_override": 512,
        "cwd": Path.cwd(),
    }
    assert use_case.requests[0].version == "1.2.3"
    assert use_case.requests[0].select_slug == "python-lint"


def test_cli_resolve_non_interactive_prints_stable_json(monkeypatch) -> None:
    use_case = QueueUseCase(
        responses=[_resolved_result(selection_mode="non_interactive_top_ranked")]
    )
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)

    def build_resolve_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_resolve_use_case", build_resolve_use_case)

    result = runner.invoke(app_module.app, ["resolve", "python lint"])

    assert result.exit_code == 0
    assert builder_kwargs == {"cwd": Path.cwd()}
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
                slug="js-lint", version="2.1.0", selection_mode="interactive_choice"
            ),
        ]
    )
    close_calls: list[str] = []

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda **_kwargs: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(app_module.app, ["resolve", "lint"], input="2\n")

    assert result.exit_code == 0
    assert "Multiple matching skills were found:" in result.stdout
    assert "tokens=120 | size=256B | published=2026-03-18T00:00:00Z" in result.stdout
    assert (
        "why ranked here: ranked above js-lint@2.1.0: closer exact name match"
        in result.stdout
    )
    assert len(use_case.requests) == 2
    assert use_case.requests[0].interaction_mode is None
    assert use_case.requests[0].prompt_capable is True
    assert use_case.requests[0].select_slug is None
    assert use_case.requests[1].interaction_mode == "never"
    assert use_case.requests[1].prompt_capable is False
    assert use_case.requests[1].select_slug == "js-lint"
    assert use_case.requests[1].selection_source == "interactive"
    assert close_calls == ["closed"]


def test_cli_resolve_select_slug_bypasses_prompt(monkeypatch) -> None:
    use_case = QueueUseCase(
        responses=[
            _resolved_result(
                slug="js-lint", version="2.1.0", selection_mode="explicit_slug"
            )
        ]
    )
    close_calls: list[str] = []

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda **_kwargs: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app, ["resolve", "lint", "--select-slug", "js-lint"]
    )

    assert result.exit_code == 0
    assert len(use_case.requests) == 1
    assert use_case.requests[0].interaction_mode is None
    assert use_case.requests[0].prompt_capable is True
    assert use_case.requests[0].select_slug == "js-lint"
    assert close_calls == ["closed"]


def test_cli_install_prints_installed_result(monkeypatch, tmp_path) -> None:
    target = tmp_path / "aptitude_state"
    export_root = tmp_path / ".codex" / "skills"
    use_case = QueueUseCase(
        responses=[_installed_result(str(target), str(export_root))]
    )
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: False)

    def build_install_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_install_use_case", build_install_use_case)

    result = runner.invoke(app_module.app, ["install", "python lint"])

    assert result.exit_code == 0
    assert builder_kwargs == {}
    assert len(use_case.requests) == 1
    assert use_case.requests[0].interaction_mode is None
    assert use_case.requests[0].prompt_capable is False
    assert use_case.requests[0].target is None
    assert use_case.requests[0].agents == ["codex"]
    assert use_case.requests[0].scope == "project"
    assert close_calls == ["closed"]
    assert "Collecting python lint" in result.stdout
    assert "Installation Summary" in result.stdout
    assert "Using resolver candidate python-lint (1.2.3)" in result.stdout
    assert "Collecting dependency dep-core (0.9.0)" in result.stdout
    assert (
        "Installing collected resolver skills: dep-core, python-lint" in result.stdout
    )
    assert "Successfully installed dep-core-0.9.0 python-lint-1.2.3" in result.stdout
    assert f"Aptitude state: {target}" in result.stdout
    assert "Lockfile: aptitude.lock.json" in result.stdout
    assert "Exported agent skills:" not in result.stdout
    assert f"codex: {export_root}" not in result.stdout


def test_cli_install_prints_pipe_separated_telemetry_when_interactive(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "aptitude_state"
    use_case = QueueUseCase(responses=[_installed_result(str(target))])

    @contextmanager
    def capture_install_telemetry():
        yield [
            StageTiming(stage="discovery", duration_ms=95.679),
            StageTiming(stage="materialization", duration_ms=18.2),
        ]

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: True)
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
            "--interaction-mode",
            "never",
        ],
    )

    assert result.exit_code == 0
    assert "Installed Skills" in result.stdout
    assert "Installation Summary" in result.stdout
    assert "Agent Exports" not in result.stdout
    assert "dep-core" in result.stdout
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
    target = tmp_path / "aptitude_state"
    installed_result = _installed_result(str(target))
    use_case = QueueUseCase(responses=[installed_result])
    close_calls: list[str] = []

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app,
        ["install", "python lint", "--json"],
    )

    assert result.exit_code == 0
    assert close_calls == ["closed"]
    assert result.stdout == (
        installed_result.model_dump_json(indent=2, exclude_none=True) + "\n"
    )


def test_cli_install_passes_selection_flag_overrides_to_builder(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "aptitude_state"
    use_case = QueueUseCase(responses=[_installed_result(str(target))])
    close_calls: list[str] = []
    builder_kwargs: dict[str, object] = {}

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)

    def build_install_use_case(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    monkeypatch.setattr(app_module, "build_install_use_case", build_install_use_case)

    result = runner.invoke(
        app_module.app,
        [
            "install",
            "python lint",
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
    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
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
    assert "APTITUDE_SERVER_BASE_URL" not in result.stderr
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

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)

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
        "cwd": Path.cwd(),
    }
    assert close_calls == ["closed"]


def test_cli_resolve_prints_structured_error_for_invalid_policy_override(
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
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
            return ["python-lint"]

        def fetch_skill_identity(self, slug: str):
            raise AssertionError(
                "slug identity lookup should not be used for this query"
            )

        def list_skill_versions(self, slug: str) -> list[VersionSummary]:
            return [
                VersionSummary(
                    coordinate=SkillCoordinate(slug="python-lint", version="1.2.3"),
                    name="Python Lint",
                    description="Lint Python files.",
                    tags=["python", "lint"],
                    headers={"runtime": "python"},
                    rendered_summary="Lint Python files.",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-28T00:00:00Z",
                    content_checksum_algorithm="sha256",
                    content_checksum_digest="digest-python-lint-1.2.3",
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
    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
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
    target = tmp_path / "aptitude_state"
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
    assert "Installing locked resolver skills: dep-core, python-lint" in result.stdout
    assert "Successfully synced dep-core-0.9.0 python-lint-1.2.3" in result.stdout
    assert f"Installed to: {target}" in result.stdout


def test_cli_sync_interactive_uses_panels(monkeypatch, tmp_path) -> None:
    lock_path = tmp_path / "aptitude.lock.json"
    target = tmp_path / "aptitude_state"
    synced_result = _synced_result(str(lock_path.resolve()), str(target))
    use_case = QueueUseCase(responses=[synced_result])

    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_sync_use_case",
        lambda: (use_case, lambda: None),
    )

    result = runner.invoke(
        app_module.app,
        ["sync", "--lock", str(lock_path), "--target", str(target)],
    )

    assert result.exit_code == 0
    assert "Sync Summary" in result.stdout
    assert "Installed Skills" in result.stdout
    assert "python-lint" in result.stdout


def test_cli_sync_json_flag_preserves_structured_output(monkeypatch, tmp_path) -> None:
    lock_path = tmp_path / "aptitude.lock.json"
    target = tmp_path / "aptitude_state"
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
    assert "Lockfile not found." in result.stderr
    assert "Path:" in result.stderr
    assert "missing.lock.json" in result.stderr
    assert "replace it with an actual file path" in result.stderr


def test_cli_install_without_query_launches_install_wizard_flow(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)

    monkeypatch.setattr(
        app_module,
        "run_cli_wizard",
        lambda **kwargs: calls.append(kwargs),
    )

    result = runner.invoke(app_module.app, ["install"])

    assert result.exit_code == 0
    assert calls == [{"initial_flow": "install"}]


@pytest.mark.parametrize("version_args", [[], ["--version", "1.2.3"]])
@pytest.mark.parametrize("confirmed", [True, False])
def test_cli_exact_install_reviews_plan_before_installing(
    monkeypatch, tmp_path, version_args, confirmed
) -> None:
    monkeypatch.delenv("CI", raising=False)
    events: list[str] = []

    class ReviewedUseCase(QueueUseCase):
        def execute(self, request, *, review_plan=None):
            events.append("plan")
            assert review_plan is not None
            review_plan(_resolved_result())
            events.append("install")
            return super().execute(request)

    use_case = ReviewedUseCase(responses=[_installed_result(str(tmp_path))])
    close_calls: list[str] = []
    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)
    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: False)

    def select_one(title, *_args, **_kwargs):
        events.append(title)
        return "project"

    def select_many(title, *_args, **_kwargs):
        events.append(title)
        return ["claude-code"]

    monkeypatch.setattr(wizard_module, "_default_select_one", select_one)
    monkeypatch.setattr(wizard_module, "_default_select_many", select_many)

    def confirm(label, _default):
        output = runner_output.getvalue()
        assert "Review Plan" in output
        assert "python-lint@1.2.3" in output
        assert "claude-code" in output
        assert "Execution Steps" in output
        events.append(label)
        return confirmed

    runner_output = StringIO()
    monkeypatch.setattr(
        app_module,
        "_stdout_console",
        lambda: Console(file=runner_output, width=120),
    )
    monkeypatch.setattr(wizard_module, "_default_confirm", confirm)
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda **_kwargs: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(app_module.app, ["install", "python-lint", *version_args])

    assert result.exit_code == 0
    assert close_calls == ["closed"]
    assert events == [
        "Install scope",
        "Agent targets",
        "plan",
        "Proceed with installation?",
        *(["install"] if confirmed else []),
    ]
    if not confirmed:
        assert use_case.requests == []
        assert "cancelled" in result.stdout.lower()
        return
    assert use_case.requests[0].query == "python-lint"
    assert use_case.requests[0].version == (version_args[1] if version_args else None)
    assert use_case.requests[0].exact is True
    assert use_case.requests[0].agents == ["claude-code"]
    assert use_case.requests[0].scope == "project"
    assert "Installed Skills" in runner_output.getvalue()
    assert "Installation Summary" in runner_output.getvalue()
    assert "Agent roots" not in runner_output.getvalue()


@pytest.mark.parametrize("args", [["--yes"], ["--json"], ["--yes", "--json"]])
def test_cli_exact_install_unattended_flags_never_prompt(monkeypatch, tmp_path, args):
    monkeypatch.delenv("CI", raising=False)
    use_case = QueueUseCase(responses=[_installed_result(str(tmp_path))])
    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)
    monkeypatch.setattr(
        app_module, "build_install_use_case", lambda **_: (use_case, lambda: None)
    )
    monkeypatch.setattr(
        wizard_module,
        "_default_select_one",
        lambda *_args, **_kwargs: pytest.fail("Unattended install prompted"),
    )
    result = runner.invoke(app_module.app, ["install", "python-lint", *args])
    assert result.exit_code == 0
    assert use_case.requests[0].exact is True
    assert use_case.requests[0].agents == ["codex"]
    assert use_case.requests[0].scope == "project"
    if "--json" in args:
        import json

        assert json.loads(result.stdout)["status"] == "installed"
        assert "\x1b[" not in result.stdout


@pytest.mark.parametrize(
    "flags, prompts, scope, agents",
    [
        (["--global"], ["Agent targets"], "global", ["claude-code"]),
        (["--agent", "claude-code"], ["Install scope"], "project", ["claude-code"]),
        (
            ["--scope", "global", "--agent", "codex", "--agent", "claude-code"],
            [],
            "global",
            ["codex", "claude-code"],
        ),
        (["--export-root", "exports", "--agent", "codex"], [], "custom", ["codex"]),
    ],
)
def test_cli_exact_install_honors_destination_flags_and_still_confirms(
    monkeypatch, tmp_path, flags, prompts, scope, agents
):
    monkeypatch.delenv("CI", raising=False)
    events = []
    builder_kwargs = {}

    class ReviewedUseCase(QueueUseCase):
        def execute(self, request, *, review_plan=None):
            assert review_plan is not None
            review_plan(_resolved_result())
            return super().execute(request)

    use_case = ReviewedUseCase(responses=[_installed_result(str(tmp_path))])

    def build(**kwargs):
        builder_kwargs.update(kwargs)
        return use_case, lambda: None

    def select_one(title, *_args, **_kwargs):
        events.append(title)
        print(title)
        return "project"

    def select_many(title, *_args, **_kwargs):
        events.append(title)
        print(title)
        return ["claude-code"]

    def confirm(title, _default):
        events.append(title)
        print(title)
        return True

    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)
    monkeypatch.setattr(app_module, "build_install_use_case", build)
    monkeypatch.setattr(wizard_module, "_default_select_one", select_one)
    monkeypatch.setattr(wizard_module, "_default_select_many", select_many)
    monkeypatch.setattr(wizard_module, "_default_confirm", confirm)
    result = runner.invoke(
        app_module.app,
        [
            "install",
            "python-lint",
            "--prefer",
            "low-cost",
            "--max-tokens",
            "500",
            *flags,
        ],
    )
    assert result.exit_code == 0, result.output
    assert events == [*prompts, "Proceed with installation?"]
    assert use_case.requests[0].scope == scope
    assert set(use_case.requests[0].agents) == set(agents)
    assert use_case.requests[0].exact is True
    assert builder_kwargs["selection_profile_override"] == "low-cost"
    assert builder_kwargs["max_token_estimate_override"] == 500
    assert "Review Plan" in result.stdout
    assert re.search(r"─{10,}\n\s*─{10,}", result.stdout) is None
    if scope == "custom":
        assert use_case.requests[0].export_root == Path("exports")


@pytest.mark.parametrize(
    "interruption", [KeyboardInterrupt, EOFError, wizard_module.WizardCancelled]
)
@pytest.mark.parametrize("stage", ["destination", "confirmation"])
def test_cli_exact_install_cancellation_closes_without_installing(
    monkeypatch, tmp_path, interruption, stage
):
    monkeypatch.delenv("CI", raising=False)
    closed = []

    def cancel(*_args, **_kwargs):
        raise interruption()

    class ReviewedUseCase(QueueUseCase):
        def execute(self, request, *, review_plan=None):
            assert review_plan is not None
            review_plan(_resolved_result())
            pytest.fail("Cancelled install executed")

    use_case = ReviewedUseCase()
    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda **_: (use_case, lambda: closed.append(True)),
    )
    monkeypatch.setattr(wizard_module, "_default_select_one", cancel)
    monkeypatch.setattr(wizard_module, "_default_confirm", cancel)
    flags = (
        ["--agent", "codex", "--scope", "project"] if stage == "confirmation" else []
    )
    result = runner.invoke(app_module.app, ["install", "python-lint", *flags])
    assert result.exit_code == 0
    assert "Installation cancelled." in result.stdout
    assert "Traceback" not in result.output
    assert closed == ([True] if stage == "confirmation" else [])


def test_cli_exact_install_in_ci_never_prompts(monkeypatch, tmp_path):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)
    use_case = QueueUseCase(responses=[_installed_result(str(tmp_path))])
    monkeypatch.setattr(
        app_module, "build_install_use_case", lambda **_: (use_case, lambda: None)
    )
    result = runner.invoke(app_module.app, ["install", "python-lint"])
    assert result.exit_code == 0
    assert len(use_case.requests) == 1
    assert "Review Plan" not in result.stdout


@pytest.mark.parametrize("flags", [[], ["--yes"]])
@pytest.mark.parametrize(
    "interruption, exit_code", [(KeyboardInterrupt, 130), (EOFError, 1)]
)
def test_cli_interrupted_install_after_approval_reports_failure(
    monkeypatch, tmp_path, flags, interruption, exit_code
):
    monkeypatch.delenv("CI", raising=False)
    closed = []

    class InterruptedUseCase:
        def execute(self, request, *, review_plan=None):
            if review_plan is not None:
                review_plan(_resolved_result())
            (tmp_path / "partial-install").write_text("partial", encoding="utf-8")
            raise interruption()

    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda **_: (InterruptedUseCase(), lambda: closed.append(True)),
    )
    monkeypatch.setattr(wizard_module, "_default_confirm", lambda *_: True)
    result = runner.invoke(
        app_module.app,
        ["install", "python-lint", "--agent", "codex", "--scope", "project", *flags],
    )
    assert result.exit_code == exit_code
    assert "partially written" in result.stderr
    assert "Installation cancelled." not in result.stdout
    assert closed == [True]


def test_cli_install_with_only_query_bypasses_wizard_when_wizard_ui_is_unavailable(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "aptitude_state"
    use_case = QueueUseCase(responses=[_installed_result(str(target))])
    close_calls: list[str] = []
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: False)
    monkeypatch.setattr(
        app_module,
        "run_cli_wizard",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda **_kwargs: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app, ["install", "python lint", "--agent", "codex"]
    )

    assert result.exit_code == 0
    assert calls == []
    assert close_calls == ["closed"]
    assert "Installation Summary" in result.stdout


def _policy_report() -> EffectivePolicyReportDto:
    return EffectivePolicyReportDto(
        cwd=str(Path("C:/Dev/apptitude-client/aptitude-client")),
        effective_selection=SelectionConfigSnapshotDto(
            profile="high-trust",
            interaction_mode="never",
            profile_source="user_config",
            interaction_mode_source="workspace_config",
        ),
        effective_policy=PolicyConfigSnapshotDto(
            source="workspace_config",
            allowed_trust_tiers=["verified", "internal"],
            allowed_lifecycle_statuses=["published"],
            max_token_estimate=500,
            max_content_size_bytes=2048,
            max_total_token_estimate=None,
            max_total_content_size_bytes=None,
        ),
        layers=[
            ConfigLayerDto(
                source="default",
                label="default",
                active=True,
                selection=SelectionConfigSnapshotDto(
                    profile="balanced",
                    interaction_mode="auto",
                ),
                policy=PolicyConfigSnapshotDto(
                    allowed_trust_tiers=["verified", "internal", "untrusted"],
                    allowed_lifecycle_statuses=[
                        "published",
                        "deprecated",
                        "archived",
                    ],
                ),
            ),
            ConfigLayerDto(
                source="system_config",
                label="system config",
                path="C:/ProgramData/aptitude/aptitude.toml",
                active=False,
            ),
            ConfigLayerDto(
                source="user_config",
                label="user config",
                path="C:/Users/test/AppData/Roaming/aptitude/aptitude.toml",
                active=True,
                selection=SelectionConfigSnapshotDto(profile="high-trust"),
            ),
            ConfigLayerDto(
                source="workspace_config",
                label="workspace config",
                path="C:/Dev/apptitude-client/aptitude-client/aptitude.toml",
                active=True,
                selection=SelectionConfigSnapshotDto(interaction_mode="never"),
                policy=PolicyConfigSnapshotDto(
                    allowed_trust_tiers=["verified", "internal"],
                    allowed_lifecycle_statuses=["published"],
                    max_token_estimate=500,
                    max_content_size_bytes=2048,
                ),
            ),
            ConfigLayerDto(
                source="environment",
                label="environment",
                active=False,
            ),
            ConfigLayerDto(
                source="cli_override",
                label="CLI override",
                active=False,
            ),
        ],
        semantics=PolicyMergeSemanticsDto(
            selection_precedence=[
                "default",
                "system_config",
                "user_config",
                "workspace_config",
                "environment",
                "cli_override",
            ],
            policy_application_order=[
                "default",
                "system_config",
                "user_config",
                "workspace_config",
                "cli_override",
            ],
            selection_rule="last non-null value wins by precedence",
            policy_rule=(
                "restrictive-only: allowed lists intersect and numeric ceilings "
                "take the minimum"
            ),
        ),
    )


def test_cli_install_with_advanced_flags_bypasses_wizard_launch(
    monkeypatch, tmp_path
) -> None:
    target = tmp_path / "aptitude_state"
    use_case = QueueUseCase(responses=[_installed_result(str(target))])
    close_calls: list[str] = []
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: True)
    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: False)
    monkeypatch.setattr(
        app_module,
        "run_cli_wizard",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        app_module,
        "build_install_use_case",
        lambda **_kwargs: (use_case, lambda: close_calls.append("closed")),
    )

    result = runner.invoke(
        app_module.app,
        [
            "install",
            "python lint",
            "--prefer",
            "low-cost",
        ],
    )

    assert result.exit_code == 0
    assert calls == []
    assert close_calls == ["closed"]
    assert "Installation Summary" in result.stdout


def test_cli_sync_without_lock_launches_sync_wizard_flow(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(app_module, "can_launch_cli_wizard", lambda: True)

    monkeypatch.setattr(
        app_module,
        "run_cli_wizard",
        lambda **kwargs: calls.append(kwargs),
    )

    result = runner.invoke(app_module.app, ["sync"])

    assert result.exit_code == 0
    assert calls == [{"initial_flow": "sync", "target": None}]


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

    monkeypatch.setattr(app_module, "_can_prompt_user", lambda: False)
    monkeypatch.setattr(
        app_module,
        "build_resolve_use_case",
        lambda **_kwargs: (
            QueueUseCase(
                error=SelectionSlugNotFoundError(
                    "lint", "missing-skill", ["python-lint"]
                )
            ),
            lambda: close_calls.append("closed"),
        ),
    )

    result = runner.invoke(
        app_module.app, ["resolve", "lint", "--select-slug", "missing-skill"]
    )

    assert result.exit_code == 1
    assert close_calls == ["closed"]
    assert "Requested selection is not available." in result.stderr
    assert "Selected slug: missing-skill" in result.stderr
    assert result.stdout == ""


def test_cli_policy_show_renders_human_readable_report(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "build_effective_policy_report", _policy_report)

    result = runner.invoke(app_module.app, ["policy", "show"])

    assert result.exit_code == 0
    assert "Effective Selection" in result.stdout
    assert "profile: high-trust (from: User config)" in result.stdout
    assert "from: Workspace config" in result.stdout
    assert "allowed trust tiers: verified, internal" in result.stdout
    assert "System config: Not found" in result.stdout
    assert "selection: more specific values win" in result.stdout
    assert (
        "install/resolve flags like --allow-trust are one-off policy overrides"
        in result.stdout
    )


def test_cli_policy_show_interactive_uses_rich_panels(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "build_effective_policy_report", _policy_report)
    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: True)

    result = runner.invoke(app_module.app, ["policy", "show"])

    assert result.exit_code == 0
    assert "Config Sources" in result.stdout
    assert "How It Works" in result.stdout
    assert "CLI override" in result.stdout
    assert (
        "Install/resolve flags like --allow-trust are one-off policy overrides."
        in result.stdout
    )


def test_cli_manifest_interactive_uses_rich_panels(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_has_interactive_output", lambda: True)

    result = runner.invoke(app_module.app, ["manifest"])

    assert result.exit_code == 0
    assert "Public Commands" in result.stdout
    assert "Advanced/Internal Commands" in result.stdout
    assert "Global Flags" in result.stdout
    assert "policy" in result.stdout
    assert "show" in result.stdout
    assert "select_slug" not in app_module._manifest_option_keys("install")
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout


def test_cli_policy_show_json_outputs_structured_report(monkeypatch) -> None:
    report = _policy_report()
    monkeypatch.setattr(app_module, "build_effective_policy_report", lambda: report)

    result = runner.invoke(app_module.app, ["policy", "show", "--json"])

    assert result.exit_code == 0
    assert result.stdout == report.model_dump_json(indent=2, exclude_none=True) + "\n"


def test_cli_policy_show_reports_invalid_system_configuration(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_effective_policy_report",
        lambda: (_ for _ in ()).throw(
            InvalidResolverConfigurationError(
                "system config",
                "allowed_trust_tiers contains unknown values: partner.",
            )
        ),
    )

    result = runner.invoke(app_module.app, ["policy", "show"])

    assert result.exit_code == 1
    assert "Invalid system configuration." in result.stderr
    assert "allowed_trust_tiers contains unknown values: partner." in result.stderr


def test_format_error_renders_environment_configuration_errors_for_humans() -> None:
    rendered = app_module._format_error(
        InvalidResolverConfigurationError(
            "environment",
            "Missing required environment variables: APTITUDE_READ_TOKEN.",
        )
    )

    assert "Aptitude is not configured." in rendered
    assert "APTITUDE_SERVER_BASE_URL" not in rendered
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
            slug="python-lint",
            version="1.2.3",
            algorithm="sha256",
            expected_digest="expected",
            actual_digest="actual",
        )
    )

    assert "Downloaded content failed integrity verification." in rendered
    assert "Skill: python-lint@1.2.3" in rendered
    assert "Expected digest: expected" in rendered
    assert "Actual digest: actual" in rendered
