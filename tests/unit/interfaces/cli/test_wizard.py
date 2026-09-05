from __future__ import annotations

import builtins
import importlib.util
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Mapping, Sequence, TypedDict, cast

import pytest
from rich.console import Console, Group
from rich.text import Text

from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    ExecutionPlanDto,
    ExecutionStepDto,
    ExportedSkillDto,
    InstalledSkillDto,
    InstallResultDto,
    LockRootDto,
    LockfileDto,
    LockedSkillDto,
    PolicyEvaluationDto,
    ResolvedGraphDto,
    ResolvedSkillNodeDto,
    ResolveCoordinateDto,
    ResolveQueryResultDto,
    ResolveSkillSummaryDto,
    SearchSkillsResultDto,
    SyncResultDto,
    TraceEntryDto,
)
from aptitude_resolver.domain.errors import DiscoveryNoCandidatesError
from aptitude_resolver.interfaces.cli import wizard as wizard_module
from aptitude_resolver.interfaces.cli.wizard import CliWizard
from aptitude_resolver.interfaces.shared import InstallWorkflowOptions
from aptitude_resolver.telemetry.metrics import StageTiming


class WindowCall(TypedDict):
    args: tuple[list[tuple[str, str]], ...]
    kwargs: dict[str, object]


class FakeWorkflowService:
    def __init__(
        self,
        *,
        search_responses: list[SearchSkillsResultDto] | None = None,
        resolve_responses: list[ResolveQueryResultDto] | None = None,
        install_responses: list[InstallResultDto] | None = None,
        sync_responses: list[SyncResultDto] | None = None,
    ) -> None:
        self.search_responses = list(search_responses or [])
        self.resolve_responses = list(resolve_responses or [])
        self.install_responses = list(install_responses or [])
        self.sync_responses = list(sync_responses or [])
        self.search_calls: list[dict[str, object]] = []
        self.resolve_calls: list[dict[str, object]] = []
        self.install_calls: list[dict[str, object]] = []
        self.sync_calls: list[dict[str, object]] = []

    def search_query(self, **kwargs: object) -> SearchSkillsResultDto:
        self.search_calls.append(kwargs)
        if self.search_responses:
            return self.search_responses.pop(0)
        return SearchSkillsResultDto(
            requested_query=str(kwargs["query"]),
            status="found",
            candidates=_selection_required_result().candidates[:1],
        )

    def resolve_query(self, **kwargs: object) -> ResolveQueryResultDto:
        self.resolve_calls.append(kwargs)
        assert self.resolve_responses
        return self.resolve_responses.pop(0)

    def install_query(self, **kwargs: object) -> InstallResultDto:
        self.install_calls.append(kwargs)
        assert self.install_responses
        return self.install_responses.pop(0)

    def sync_lock(self, **kwargs: object) -> SyncResultDto:
        self.sync_calls.append(kwargs)
        assert self.sync_responses
        return self.sync_responses.pop(0)


def _select_direct_install_option(select_calls: list[str]) -> Callable[..., str]:
    def select_one(title: str, *_args: object, **_kwargs: object) -> str:
        select_calls.append(title)
        if title == "Select candidate":
            return "python-lint"
        if title == "Install scope":
            return "project"
        return "auto"

    return select_one


def _select_direct_install_agent_targets(
    select_calls: list[str],
    agents: list[str] | None = None,
) -> Callable[..., list[str]]:
    def select_many(title: str, *_args: object, **_kwargs: object) -> list[str]:
        select_calls.append(title)
        if title == "Agent targets":
            return list(agents or ["codex"])
        return []

    return select_many


def _select_direct_install_event(events: list[str]) -> Callable[..., str]:
    def select_one(title: str, *_args: object, **_kwargs: object) -> str:
        events.append(f"select:{title}")
        if title == "Select candidate":
            return "python-lint"
        if title == "Install scope":
            return "project"
        return "auto"

    return select_one


def _select_direct_install_agent_event(events: list[str]) -> Callable[..., list[str]]:
    def select_many(title: str, *_args: object, **_kwargs: object) -> list[str]:
        events.append(f"select-many:{title}")
        if title == "Agent targets":
            return ["codex"]
        return []

    return select_many


def _record_separator(
    events: list[str], original_print_step_separator: Callable[[], None]
) -> Callable[[], None]:
    def wrapped() -> None:
        events.append("separator")
        original_print_step_separator()

    return wrapped


def _record_prompt(events: list[str], answers: Iterator[str]) -> Callable[..., str]:
    def prompt_text(label: str, *_args: object, **_kwargs: object) -> str:
        events.append(f"prompt:{label}")
        return next(answers)

    return prompt_text


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
                    headers={"runtime": "python"},
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
                selection_details=["tokens=120", "size=256B"],
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
                selection_details=["tokens=250", "size=320B"],
                selection_reason="broader match",
            ),
        ],
        trace=[],
    )


def _installed_result(
    materialized_root: str = str(Path("aptitude_state")),
) -> InstallResultDto:
    return InstallResultDto(
        requested_query="lint",
        status="installed",
        selection_mode="interactive_choice",
        selected_coordinate=ResolveCoordinateDto(slug="js-lint", version="2.1.0"),
        graph=ResolvedGraphDto(
            root=ResolveCoordinateDto(slug="js-lint", version="2.1.0"),
            nodes=[],
            edges=[],
            install_order=[ResolveCoordinateDto(slug="js-lint", version="2.1.0")],
            conflicts=[],
        ),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="lint",
                requested_version=None,
                selected_node_id="js-lint@2.1.0",
                selection_mode="interactive_choice",
            ),
            nodes=[],
            edges=[],
            install_order=["js-lint@2.1.0"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id="js-lint@2.1.0",
                    skill="js-lint",
                    version="2.1.0",
                    artifact_ref="/skills/js-lint/2.1.0/content",
                    action="materialize_local_skill",
                )
            ]
        ),
        installed_skills=[
            InstalledSkillDto(
                slug="js-lint",
                version="2.1.0",
                install_path=str(
                    Path(materialized_root) / "skills" / "js-lint" / "2.1.0"
                ),
            )
        ],
        exported_skills=[
            ExportedSkillDto(
                agent="codex",
                scope="project",
                slug="js-lint",
                version="2.1.0",
                destination_path=str(Path(".codex") / "skills" / "js-lint"),
                skill_markdown_path=str(
                    Path(".codex") / "skills" / "js-lint" / "SKILL.md"
                ),
            )
        ],
        materialized_root=materialized_root,
        lock_path=str(Path("aptitude.lock.json")),
        trace=[],
    )


def _synced_result(
    materialized_root: str = str(Path("aptitude_state")),
) -> SyncResultDto:
    installed_result = _installed_result(materialized_root=materialized_root)
    assert installed_result.lockfile is not None
    assert installed_result.execution_plan is not None
    return SyncResultDto(
        lock_path=str(Path("aptitude.lock.json")),
        requested_query=installed_result.requested_query,
        status="synced",
        selection_mode=installed_result.selection_mode,
        selected_coordinate=installed_result.selected_coordinate,
        lockfile=installed_result.lockfile,
        execution_plan=installed_result.execution_plan,
        installed_skills=installed_result.installed_skills,
        materialized_root=installed_result.materialized_root,
        trace=installed_result.trace,
    )


def test_cli_wizard_resolves_candidate_and_installs_selected_skill() -> None:
    service = FakeWorkflowService(
        resolve_responses=[
            _resolved_result(
                slug="js-lint", version="2.1.0", selection_mode="interactive_choice"
            ),
        ],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["lint"])
    selections = iter(["install", "js-lint", "project"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        select_many=lambda *_, **__: ["codex"],
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert len(service.resolve_calls) == 1
    assert service.resolve_calls[0]["select_slug"] == "js-lint"
    assert service.resolve_calls[0]["selection_source"] == "interactive"
    assert service.install_calls[0]["query"] == "lint"
    assert service.install_calls[0]["select_slug"] == "js-lint"
    assert service.install_calls[0]["selection_source"] == "interactive"
    assert service.install_calls[0]["agents"] == ["codex"]
    assert service.install_calls[0]["scope"] == "project"
    output = transcript.getvalue()
    assert "Installation Summary" in output
    assert str(Path(".codex") / "skills" / "js-lint") in output
    assert str(Path("aptitude.lock.json")) in output
    assert str(Path("aptitude_state") / "skills" / "js-lint" / "2.1.0") not in output


def test_installation_summary_uses_light_subsections() -> None:
    panel = wizard_module._render_materialization_panel(
        _installed_result(),
        title="Installation Summary",
        footer="Install telemetry | Discovery 95.7ms | Materialization 18.2ms",
    )

    assert isinstance(panel.renderable, Group)
    sections = cast(Group, panel.renderable).renderables
    headings = [
        renderable
        for renderable in sections
        if isinstance(renderable, Text)
        and renderable.plain in {"Installed Skills", "Lockfile", "Telemetry"}
    ]
    assert [heading.plain for heading in headings] == [
        "Installed Skills",
        "Lockfile",
        "Telemetry",
    ]
    assert all(heading.style == wizard_module.THEME.text_detail for heading in headings)

    transcript = StringIO()
    Console(file=transcript, force_terminal=False, color_system=None).print(panel)
    output = transcript.getvalue()
    assert "Install telemetry |" not in output
    assert "Discovery 95.7ms | Materialization 18.2ms" in output


def test_cli_wizard_lists_candidates_before_destination_prompts() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result(slug="js-lint", version="2.1.0")],
        install_responses=[_installed_result()],
    )
    events: list[str] = []

    def search_query(**kwargs: object) -> SearchSkillsResultDto:
        return SearchSkillsResultDto(
            requested_query=str(kwargs["query"]),
            status="found",
            candidates=_selection_required_result().candidates,
        )

    service.search_query = search_query  # type: ignore[method-assign]

    def select_one(title: str, *_args: object, **_kwargs: object) -> str:
        events.append(title)
        if title == "Choose a flow":
            return "install"
        if title == "Select candidate":
            return "js-lint"
        return "project"

    def select_many(*_args: object, **_kwargs: object) -> list[str]:
        events.append("Agent targets")
        return ["codex"]

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=StringIO(), force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "lint",
        select_one=select_one,
        select_many=select_many,
        confirm=lambda *_, **__: True,
    )

    wizard.run()

    assert events.index("Select candidate") < events.index("Install scope")
    assert events.index("Select candidate") < events.index("Agent targets")


def test_cli_wizard_installs_to_multiple_selected_agent_targets() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    selections = iter(["install", "python-lint", "project"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "postman primary skill",
        select_one=lambda *_, **__: next(selections),
        select_many=lambda *_, **__: ["codex", "cursor"],
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert service.install_calls[0]["agents"] == ["codex", "cursor"]


def test_cli_wizard_multi_agent_selection_expands_detected_targets(monkeypatch) -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    selections = iter(["install", "python-lint", "project"])
    confirmations = iter([True])
    monkeypatch.setattr(
        wizard_module,
        "detect_available_agent_targets",
        lambda: ["codex", "cursor"],
    )

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "postman primary skill",
        select_one=lambda *_, **__: next(selections),
        select_many=lambda *_, **__: ["detected", "codex"],
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert service.install_calls[0]["agents"] == ["codex", "cursor"]


def test_cli_wizard_prints_pipe_separated_install_telemetry() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["python lint"])
    selections = iter(["install", "python-lint", "project"])
    confirmations = iter([True])

    @contextmanager
    def capture_install_telemetry():
        yield [
            StageTiming(stage="discovery", duration_ms=95.679),
            StageTiming(stage="materialization", duration_ms=18.2),
        ]

    original_capture = wizard_module.capture_cli_telemetry
    wizard_module.capture_cli_telemetry = capture_install_telemetry
    try:
        wizard = CliWizard(
            workflow_service=service,
            console=Console(file=transcript, force_terminal=False, color_system=None),
            prompt_text=lambda *_, **__: next(answers),
            select_one=lambda *_, **__: next(selections),
            select_many=lambda *_, **__: ["codex"],
            confirm=lambda *_, **__: next(confirmations),
        )

        wizard.run()
    finally:
        wizard_module.capture_cli_telemetry = original_capture

    assert "Installation Summary" in transcript.getvalue()
    assert "Resolve query telemetry" not in transcript.getvalue()
    assert "Telemetry" in transcript.getvalue()
    assert "Discovery 95.7ms | Materialization 18.2ms" in transcript.getvalue()


def test_cli_wizard_prints_telemetry_with_trailing_blank_line() -> None:
    transcript = StringIO()
    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: "install",
        confirm=lambda *_, **__: False,
    )

    wizard._print_operation_telemetry(  # type: ignore[attr-defined]
        "Resolve query",
        [StageTiming(stage="discovery", duration_ms=84.8)],
    )

    output = transcript.getvalue()
    assert output.startswith("Resolve query telemetry")
    assert output.endswith("\n\n")


def test_cli_wizard_header_uses_filled_aptitude_wordmark() -> None:
    transcript = StringIO()
    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: "install",
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    output = transcript.getvalue()
    assert "Aptitude Resolver" in output
    assert "   ______          __" in output
    assert "wizard launcher" not in output
    assert "[enter] confirm  [↑↓] move  [q] quit" not in output
    assert "Choose a flow" not in output
    assert "Capability Map" not in output


def test_cli_wizard_header_includes_resolver_package_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcript = StringIO()
    monkeypatch.setattr(wizard_module, "resolve_cli_version", lambda: "0.2.8")
    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: "exit",
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    assert "Aptitude Resolver 0.2.8 - " in transcript.getvalue()


def test_cli_wizard_header_styles_the_complete_version_consistently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    transcript = StringIO()
    monkeypatch.setattr(wizard_module, "resolve_cli_version", lambda: "0.2.8")
    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(
            file=transcript,
            force_terminal=True,
            color_system="truecolor",
        ),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: "exit",
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    assert "\x1b[1;36m0.2.8\x1b[0m" in transcript.getvalue()


def test_cli_wizard_passes_flow_descriptions_to_selector() -> None:
    transcript = StringIO()
    select_calls: list[dict[str, object]] = []

    def select_one(
        title: str,
        options: Sequence[tuple[str, object]],
        help_text: str | None = None,
        descriptions: Mapping[object, str] | None = None,
        **_kwargs: object,
    ) -> str:
        select_calls.append(
            {
                "title": title,
                "help_text": help_text,
                "descriptions": descriptions,
            }
        )
        return "exit"

    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=select_one,
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    assert select_calls[0]["title"] == "Choose a flow"
    assert select_calls[0]["descriptions"] == {
        "install": "Guided fresh planning and materialization.",
        "sync": "Replay an existing lockfile into a local workspace.",
        "help": "Show the capability map and command guide.",
        "exit": "Leave the wizard without running a command.",
    }


def test_cli_wizard_header_separator_is_followed_by_blank_line() -> None:
    transcript = StringIO()

    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: "exit",
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    separator = wizard_module._render_step_separator(wizard._console.size.width)
    assert f"{separator}\n\nExited." in transcript.getvalue()


def test_cli_wizard_does_not_print_back_to_back_separators_before_launcher_menu() -> (
    None
):
    transcript = StringIO()

    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: "exit",
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    separator = wizard_module._render_step_separator(wizard._console.size.width)
    assert f"{separator}\n\n{separator}" not in transcript.getvalue()


def test_active_menu_description_follows_hovered_option() -> None:
    descriptions = {
        "install": "Guided fresh planning and materialization.",
        "sync": "Replay an existing lockfile into a local workspace.",
    }

    assert (
        wizard_module._active_menu_description(
            [("Install from query", "install"), ("Sync from lockfile", "sync")],
            index=1,
            descriptions=descriptions,
        )
        == "Replay an existing lockfile into a local workspace."
    )


def test_render_choice_line_appends_active_description_inline() -> None:
    assert (
        wizard_module._render_choice_line(
            "Install from query",
            active=True,
            description="Guided fresh planning and materialization.",
        )
        == "● Install from query - Guided fresh planning and materialization."
    )
    assert (
        wizard_module._render_choice_line(
            "Sync from lockfile",
            active=False,
            description="Replay an existing lockfile into a local workspace.",
        )
        == "○ Sync from lockfile"
    )


def test_candidate_menu_uses_borderless_columns_and_active_only_details() -> None:
    candidate = (
        _selection_required_result()
        .candidates[0]
        .model_copy(
            update={
                "maturity_score": 0.9,
                "security_score": 0.95,
                "install_count": 123,
                "star_count": 45,
            }
        )
    )

    header, options, descriptions = wizard_module._candidate_menu_columns(
        [candidate],
        candidate_limit=5,
    )

    assert header == (
        "Skill                            Version    Maturity   Security   Installs   Stars"
    )
    assert options == [("python-lint                     ", "python-lint")]
    assert descriptions == {
        "python-lint": "1.2.3      0.90       0.95            123      45"
    }


def test_candidate_menu_uses_configured_limit_with_five_visible_rows() -> None:
    candidate = _selection_required_result().candidates[0]
    candidates = [
        candidate.model_copy(update={"slug": f"skill-{index}"}) for index in range(12)
    ]

    _, options, descriptions = wizard_module._candidate_menu_columns(
        candidates,
        candidate_limit=7,
    )

    assert wizard_module.CANDIDATE_VIEWPORT_SIZE == 5
    assert [value for _, value in options] == [f"skill-{index}" for index in range(7)]
    assert list(descriptions) == [f"skill-{index}" for index in range(7)]


def test_candidate_menu_renders_missing_metrics_as_em_dash() -> None:
    candidate = _selection_required_result().candidates[0]

    _, _, descriptions = wizard_module._candidate_menu_columns(
        [candidate],
        candidate_limit=5,
    )

    assert (
        descriptions["python-lint"]
        == "1.2.3      —          —                 —       —"
    )


def test_render_wordmark_supports_alternate_banner_style() -> None:
    rendered = wizard_module._render_wordmark(style="block")

    assert "░▒▓██████▓▒░" in rendered
    assert "Aptitud" not in rendered


def test_format_plan_summary_row_aligns_one_label_value_pair() -> None:
    assert (
        wizard_module._format_plan_summary_row(
            ("Runtime", "unknown"),
        )
        == "Runtime        : unknown"
    )
    assert (
        wizard_module._format_plan_summary_row(
            ("Scope", "project"),
        )
        == "Scope          : project"
    )


def test_render_plan_omits_runtime_and_trust() -> None:
    output = StringIO()
    Console(file=output, width=120, force_terminal=False).print(
        wizard_module._render_plan_panel(
            _resolved_result(),
            scope="project",
            export_roots={"codex": Path(".codex/skills")},
        )
    )
    rendered = output.getvalue()

    assert "Lifecycle" in rendered
    assert "Runtime" not in rendered
    assert "Trust" not in rendered


def test_cli_wizard_help_shows_capability_map_only_on_demand() -> None:
    transcript = StringIO()
    selections = iter(["help", "exit"])

    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: next(selections),
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    output = transcript.getvalue()
    assert "Capability Map" in output
    assert "Public commands" in output
    assert "Advanced/internal" in output
    assert "Global flags" in output
    assert 'resolve  aptitude resolve "query" [planning flags]' in output
    assert "--version" in output
    assert "--help" in output
    assert "--install-completion" not in output
    assert "--show-completion" not in output
    assert "aptitude manifest" in output


def test_cli_wizard_can_start_directly_in_install_flow_without_launcher() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["postman primary skill"])
    selections = iter(["python-lint", "project"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        select_many=lambda *_, **__: ["codex"],
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run(initial_flow="install")

    output = transcript.getvalue()
    assert "Choose a flow" not in output
    assert "guided install flow" not in output
    assert service.install_calls[0]["query"] == "postman primary skill"


def test_cli_wizard_starts_at_candidate_selection_with_initial_query() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    prompt_calls: list[tuple[str, str | None, bool]] = []
    select_calls: list[str] = []
    confirmations = iter([True])

    def prompt_text(
        label: str,
        default: str | None,
        *,
        large: bool = False,
    ) -> str:
        prompt_calls.append((label, default, large))
        return ""

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=prompt_text,
        select_one=_select_direct_install_option(select_calls),
        select_many=_select_direct_install_agent_targets(select_calls),
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run(initial_flow="install", initial_query="postman primary skill")

    output = transcript.getvalue()
    assert "Choose a flow" not in output
    assert prompt_calls == []
    assert select_calls[:3] == ["Select candidate", "Install scope", "Agent targets"]
    assert service.resolve_calls[0]["query"] == "postman primary skill"
    options = cast(InstallWorkflowOptions, service.resolve_calls[0]["options"])
    assert options.selection_profile == "balanced"
    assert options.interaction_mode == "auto"
    assert service.install_calls[0]["query"] == "postman primary skill"


def test_cli_wizard_direct_install_flow_selects_candidate_before_destination() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    events: list[str] = []
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=_select_direct_install_event(events),
        select_many=_select_direct_install_agent_event(events),
        confirm=lambda *_, **__: next(confirmations),
    )
    original_print_step_separator = wizard._print_step_separator
    wizard._print_step_separator = _record_separator(  # type: ignore[method-assign]
        events, original_print_step_separator
    )

    wizard.run(initial_flow="install", initial_query="postman primary skill")

    candidate_index = events.index("select:Select candidate")
    scope_index = events.index("select:Install scope")
    assert events[candidate_index + 1 : scope_index] == ["separator"]


def test_cli_wizard_separates_install_scope_from_agent_targets() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    events: list[str] = []
    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=StringIO(), force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=_select_direct_install_event(events),
        select_many=_select_direct_install_agent_event(events),
        confirm=lambda *_, **__: True,
    )
    original_print_step_separator = wizard._print_step_separator
    wizard._print_step_separator = _record_separator(  # type: ignore[method-assign]
        events, original_print_step_separator
    )

    wizard.run(initial_flow="install", initial_query="postman primary skill")

    scope_index = events.index("select:Install scope")
    agents_index = events.index("select-many:Agent targets")
    assert events[scope_index + 1 : agents_index] == ["separator"]


def test_cli_wizard_sync_flow_runs_after_selecting_sync() -> None:
    service = FakeWorkflowService(sync_responses=[_synced_result()])
    transcript = StringIO()
    answers = iter(["aptitude.lock.json", "demo_sync"])
    selections = iter(["sync"])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    assert len(service.sync_calls) == 1
    assert service.sync_calls[0]["lock_path"] == Path("aptitude.lock.json")
    assert service.sync_calls[0]["target"] == Path("demo_sync")
    assert "Installed Skills" in transcript.getvalue()


def test_cli_wizard_direct_sync_flow_prints_one_separator_before_lockfile_prompt() -> (
    None
):
    service = FakeWorkflowService(sync_responses=[_synced_result()])
    transcript = StringIO()
    answers = iter(["aptitude.lock.json", "demo_sync"])
    events: list[str] = []

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=_record_prompt(events, answers),
        select_one=lambda *_, **__: "sync",
        confirm=lambda *_, **__: False,
    )
    original_print_step_separator = wizard._print_step_separator
    wizard._print_step_separator = _record_separator(  # type: ignore[method-assign]
        events, original_print_step_separator
    )

    wizard.run(initial_flow="sync")

    assert events[:2] == ["separator", "prompt:Lockfile path"]


def test_cli_wizard_uses_large_text_prompt_only_for_install_query() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    prompt_calls: list[tuple[str, str | None, bool]] = []
    answers = iter(["postman primary skill"])
    selections = iter(["install", "python-lint", "project"])
    confirmations = iter([True])

    def prompt_text(
        label: str,
        default: str | None,
        *,
        large: bool = False,
    ) -> str:
        prompt_calls.append((label, default, large))
        return next(answers)

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=prompt_text,
        select_one=lambda *_, **__: next(selections),
        select_many=lambda *_, **__: ["codex"],
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert prompt_calls == [("Install query", None, True)]


def test_cli_wizard_install_destination_excludes_return_options() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["Postman Primary Skill"])
    selections = iter(["install", "python-lint", "project"])
    confirmations = iter([True])
    install_scope_options: list[str] = []
    agent_target_options: list[str] = []

    def select_one(
        title: str,
        options: Sequence[tuple[str, object]],
        *_args: object,
        **_kwargs: object,
    ) -> object:
        if title == "Install scope":
            install_scope_options.extend(label for label, _ in options)
        return next(selections)

    def select_many(
        title: str,
        options: Sequence[tuple[str, object]],
        *_args: object,
        **_kwargs: object,
    ) -> list[str]:
        if title == "Agent targets":
            agent_target_options.extend(label for label, _ in options)
        return ["codex"]

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=select_one,
        select_many=select_many,
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert "Return" not in install_scope_options
    assert "Return" not in agent_target_options
    assert service.install_calls[0]["query"] == "Postman Primary Skill"


def test_cli_wizard_prints_step_separators_between_install_steps() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["postman primary skill"])
    selections = iter(["install", "python-lint", "project"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        select_many=lambda *_, **__: ["codex"],
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    expected_separator = wizard_module._render_step_separator(
        wizard._console.size.width
    )
    assert transcript.getvalue().count(expected_separator) >= 5


def test_cli_wizard_prints_one_separator_between_query_and_candidate_menu() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    events: list[str] = []
    answers = iter(["python lint"])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=StringIO(), force_terminal=False, color_system=None),
        prompt_text=_record_prompt(events, answers),
        select_one=_select_direct_install_event(events),
        select_many=_select_direct_install_agent_event(events),
        confirm=lambda *_, **__: True,
    )
    original_print_step_separator = wizard._print_step_separator
    wizard._print_step_separator = _record_separator(  # type: ignore[method-assign]
        events, original_print_step_separator
    )

    wizard.run()

    query_index = events.index("prompt:Install query")
    candidate_index = events.index("select:Select candidate")
    assert events[query_index + 1 : candidate_index].count("separator") == 1


def test_cli_wizard_status_spinners_use_theme_accent() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        sync_responses=[_synced_result()],
    )
    console = Console(file=StringIO(), force_terminal=False, color_system=None)
    spinner_styles: list[str | None] = []

    @contextmanager
    def status(*_args: object, **kwargs: object):
        spinner_styles.append(cast(str | None, kwargs.get("spinner_style")))
        yield

    console.status = status  # type: ignore[assignment]
    wizard = CliWizard(
        workflow_service=service,
        console=console,
        prompt_text=lambda *_, **__: "",
    )
    options = wizard_module.build_workflow_options(
        prefer="balanced",
        interaction_mode="auto",
    )

    wizard._search(query="lint", options=options)
    wizard._resolve(query="lint", select_slug="python-lint", options=options)
    wizard._run_sync_flow()

    assert spinner_styles == [
        wizard_module.THEME.accent,
        wizard_module.THEME.accent,
        wizard_module.THEME.accent,
    ]


@pytest.mark.parametrize("operation", ["search", "resolve", "sync"])
def test_cli_wizard_status_spinner_spacing_matches_visible_output(
    operation: str,
) -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        sync_responses=[_synced_result()],
    )
    transcript = StringIO()
    console = Console(file=transcript, force_terminal=False, color_system=None)

    @contextmanager
    def status(*_args: object, **_kwargs: object):
        transcript.write("spinner\n")
        yield

    console.status = status  # type: ignore[assignment]
    wizard = CliWizard(
        workflow_service=service,
        console=console,
        prompt_text=lambda *_, **__: "",
    )
    options = wizard_module.build_workflow_options(
        prefer="balanced",
        interaction_mode="auto",
    )

    if operation == "search":
        wizard._search(query="lint", options=options)
    elif operation == "resolve":
        wizard._resolve(query="lint", select_slug="python-lint", options=options)
    else:
        wizard._print_step_separator = lambda: None  # type: ignore[method-assign]
        wizard._run_sync_flow()

    expected = "spinner\n" if operation == "resolve" else "\nspinner\n\n"
    assert transcript.getvalue() == expected


@pytest.mark.parametrize("operation", ["search", "resolve", "sync"])
def test_cli_wizard_exception_status_spacing_matches_visible_telemetry(
    operation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeWorkflowService()
    transcript = StringIO()
    console = Console(file=transcript, force_terminal=False, color_system=None)

    @contextmanager
    def status(*_args: object, **_kwargs: object):
        transcript.write("spinner\n")
        yield

    @contextmanager
    def capture_telemetry():
        yield [StageTiming(stage="discovery", duration_ms=12.3)]

    console.status = status  # type: ignore[assignment]
    monkeypatch.setattr(wizard_module, "capture_cli_telemetry", capture_telemetry)
    wizard = CliWizard(
        workflow_service=service,
        console=console,
        prompt_text=lambda *_, **__: "",
    )
    options = wizard_module.build_workflow_options(
        prefer="balanced",
        interaction_mode="auto",
    )

    if operation == "search":

        def fail_search(**_kwargs: object) -> SearchSkillsResultDto:
            raise RuntimeError("search failed")

        service.search_query = fail_search  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="search failed"):
            wizard._search(query="lint", options=options)
    elif operation == "resolve":

        def fail_resolve(**_kwargs: object) -> ResolveQueryResultDto:
            raise RuntimeError("resolve failed")

        service.resolve_query = fail_resolve  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="resolve failed"):
            wizard._resolve(query="lint", select_slug="python-lint", options=options)
    else:

        def fail_sync(**_kwargs: object) -> SyncResultDto:
            raise RuntimeError("sync failed")

        service.sync_lock = fail_sync  # type: ignore[method-assign]
        wizard._print_step_separator = lambda: None  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="sync failed"):
            wizard._run_sync_flow()

    output = transcript.getvalue()
    if operation == "resolve":
        assert output == "spinner\n"
    elif operation == "search":
        assert output == "\nspinner\n\n"
        assert "telemetry" not in output
    else:
        assert "\nspinner\n\n" in output
        assert "spinner\n\n\n" not in output
        assert "telemetry" in output


def test_cli_wizard_retries_install_query_after_no_matches() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["dsas", "postman primary skill"])
    selections = iter(
        [
            "install",
            "python-lint",
            "project",
        ]
    )
    confirmations = iter([True])

    def search_query(**kwargs: object) -> SearchSkillsResultDto:
        query = kwargs["query"]
        if query == "dsas":
            raise DiscoveryNoCandidatesError("dsas")
        return SearchSkillsResultDto(
            requested_query=str(query),
            status="found",
            candidates=_selection_required_result().candidates[:1],
        )

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        select_many=lambda *_, **__: ["codex"],
        confirm=lambda *_, **__: next(confirmations),
    )
    service.search_query = search_query  # type: ignore[method-assign]

    wizard.run()

    output = transcript.getvalue()
    assert "No matching skills were found." in output
    assert "Try a more specific query or adjust any restrictive policy flags." in output
    assert any(corner in output for corner in ("╭", "┌", "+"))
    assert "Query: dsas" in output
    assert service.install_calls[0]["query"] == "postman primary skill"


def test_default_prompt_text_falls_back_to_builtin_input(monkeypatch) -> None:
    monkeypatch.setattr(builtins, "input", lambda _: "postman primary skill")

    assert (
        wizard_module._default_prompt_text("Install query", None)
        == "postman primary skill"
    )


def test_wizard_module_imports_without_unix_terminal_modules(monkeypatch) -> None:
    module_path = Path("src/aptitude_resolver/interfaces/cli/wizard.py")
    spec = importlib.util.spec_from_file_location(
        "wizard_without_unix_terminal_modules", module_path
    )
    assert spec is not None
    assert spec.loader is not None

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"termios", "tty"}:
            raise ModuleNotFoundError(f"No module named '{name}'", name=name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.termios is None
    assert module.tty is None


def test_can_launch_cli_wizard_rejects_non_unicode_console_output(
    monkeypatch,
) -> None:
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        wizard_module.sys,
        "stdout",
        SimpleNamespace(isatty=lambda: True, encoding="cp1255"),
    )

    assert wizard_module.can_launch_cli_wizard() is False


def test_default_select_one_falls_back_to_number_prompt_when_not_a_tty(
    monkeypatch,
) -> None:
    responses = iter(["2"])
    monkeypatch.setattr(builtins, "input", lambda _: next(responses))
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: False)

    result = wizard_module._default_select_one(
        "Install scope",
        [("Project", "project"), ("Global", "global")],
        "Choose where the selected agent should see this skill.",
    )

    assert result == "global"


def test_default_select_many_falls_back_to_comma_separated_number_prompt(
    monkeypatch,
) -> None:
    responses = iter(["1, 2"])
    monkeypatch.setattr(builtins, "input", lambda _: next(responses))
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: False)

    result = wizard_module._default_select_many(
        "Agent targets",
        [("Codex", "codex"), ("Cursor", "cursor"), ("Return", "__return__")],
        "Choose one or more agent formats and roots to export into.",
    )

    assert result == ["codex", "cursor"]


def test_fallback_select_one_uses_number_prompt_when_raw_terminal_control_is_unavailable(
    monkeypatch,
) -> None:
    responses = iter(["2"])
    monkeypatch.setattr(builtins, "input", lambda _: next(responses))
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module, "termios", None)
    monkeypatch.setattr(wizard_module, "tty", None)

    result = wizard_module._fallback_select_one(
        "Install scope",
        [("Project", "project"), ("Global", "global")],
        "Choose where the selected agent should see this skill.",
    )

    assert result == "global"


def test_fallback_select_one_renders_candidate_divider_and_trailing_hint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def read_choice(prompt: str) -> str:
        print(prompt, end="")
        return "1"

    monkeypatch.setattr(builtins, "input", read_choice)
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: False)

    candidate = (
        _selection_required_result()
        .candidates[0]
        .model_copy(
            update={
                "maturity_score": 0.9,
                "security_score": 0.95,
                "install_count": 123,
                "star_count": 45,
            }
        )
    )
    header, options, descriptions = wizard_module._candidate_menu_columns(
        [candidate],
        candidate_limit=5,
    )
    result = wizard_module._fallback_select_one(
        "Select candidate",
        options,
        "Pick a skill.",
        descriptions,
        column_header=header,
    )

    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(
            file=wizard_module.sys.stdout, force_terminal=False, color_system=None
        ),
    )
    wizard._print_step_separator()
    output = capsys.readouterr().out
    assert result == "python-lint"
    lines = output.splitlines()
    header_line = next(line for line in lines if header in line)
    divider_line = next(line for line in lines if "─" in line)
    row_line = next(line for line in lines if "python-lint" in line)
    assert header_line.index("Skill") == row_line.index("python-lint")
    assert header_line.index("Version") == row_line.index("1.2.3")
    assert header_line.index("Maturity") == row_line.index("0.90")
    assert header_line.index("Security") == row_line.index("0.95")
    assert divider_line.index("─") == header_line.index("Skill")
    assert (
        "[↑↓] move  [enter] confirm  [q] cancel\n\nSelect option by number: \n"
        in output
    )
    separator = wizard_module._render_step_separator(wizard._console.size.width)
    assert f"Select option by number: \n{separator}\n" in output


def test_fallback_select_many_uses_number_prompt_when_raw_terminal_control_is_unavailable(
    monkeypatch,
) -> None:
    responses = iter(["1 2"])
    monkeypatch.setattr(builtins, "input", lambda _: next(responses))
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module, "termios", None)
    monkeypatch.setattr(wizard_module, "tty", None)

    result = wizard_module._fallback_select_many(
        "Agent targets",
        [("Codex", "codex"), ("Cursor", "cursor")],
        "Choose one or more agent formats and roots to export into.",
    )

    assert result == ["codex", "cursor"]


def test_fallback_select_many_leaves_one_blank_line_after_trailing_hint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def read_choice(prompt: str) -> str:
        print(prompt, end="")
        return "1"

    monkeypatch.setattr(builtins, "input", read_choice)
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: False)

    result = wizard_module._fallback_select_many(
        "Agent targets",
        [("Codex", "codex")],
        "Choose one or more agent formats and roots to export into.",
    )

    output = capsys.readouterr().out
    assert result == ["codex"]
    assert output.endswith(
        "[↑↓] move  [space] select  [enter] confirm  [q] cancel\n\n"
        "Select one or more options by number, comma-separated: \n"
    )


def test_step_separator_has_one_empty_line_before_and_after() -> None:
    transcript = StringIO()
    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "",
        select_one=lambda *_, **__: "exit",
        confirm=lambda *_, **__: False,
    )

    hint = "[↑↓] move  [enter] confirm  [q] cancel"
    transcript.write(f"{hint}\n\n")
    wizard._print_step_separator()

    separator = wizard_module._render_step_separator(wizard._console.size.width)
    assert transcript.getvalue().endswith(f"{hint}\n\n{separator}\n\n")


def test_default_select_one_allows_quit_when_not_a_tty(monkeypatch) -> None:
    responses = iter(["q"])
    monkeypatch.setattr(builtins, "input", lambda _: next(responses))
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: False)

    try:
        wizard_module._default_select_one(
            "Choose a flow",
            [("Install from query", "install"), ("Exit", "exit")],
        )
    except wizard_module.WizardCancelled:
        return

    raise AssertionError("Expected WizardCancelled when entering q in fallback mode.")


def test_default_prompt_text_uses_full_width_large_tty_prompt(monkeypatch) -> None:
    frame_calls: list[dict[str, object]] = []
    text_area_calls: list[dict[str, object]] = []
    hsplit_calls: list[dict[str, object]] = []
    vsplit_calls: list[dict[str, object]] = []
    binding_calls: list[tuple[object, ...]] = []
    window_calls: list[WindowCall] = []

    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys, "platform", "linux")

    prompt_toolkit_module = ModuleType("prompt_toolkit")
    setattr(prompt_toolkit_module, "prompt", lambda *_args, **_kwargs: "")

    application_module = ModuleType("prompt_toolkit.application")

    class FakeApplication:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def run(self) -> str:
            return "typed query"

    setattr(application_module, "Application", FakeApplication)

    key_binding_module = ModuleType("prompt_toolkit.key_binding")

    class FakeKeyBindings:
        def add(self, *_keys):
            binding_calls.append(_keys)

            def decorator(func):
                return func

            return decorator

    setattr(key_binding_module, "KeyBindings", FakeKeyBindings)

    layout_module = ModuleType("prompt_toolkit.layout")
    setattr(
        layout_module,
        "Layout",
        lambda container, focused_element=None: SimpleNamespace(
            container=container,
            focused_element=focused_element,
        ),
    )

    containers_module = ModuleType("prompt_toolkit.layout.containers")

    def fake_hsplit(children, **kwargs):
        hsplit_calls.append({"children": children, **kwargs})
        return SimpleNamespace(children=children, kwargs=kwargs)

    setattr(containers_module, "HSplit", fake_hsplit)

    def fake_vsplit(children, **kwargs):
        vsplit_calls.append({"children": children, **kwargs})
        return SimpleNamespace(children=children, kwargs=kwargs)

    setattr(containers_module, "VSplit", fake_vsplit)

    def fake_window(
        *args: list[tuple[str, str]],
        **kwargs: object,
    ) -> SimpleNamespace:
        window_calls.append({"args": args, "kwargs": kwargs})
        return SimpleNamespace(
            args=args,
            kwargs=kwargs,
        )

    setattr(containers_module, "Window", fake_window)

    dimension_module = ModuleType("prompt_toolkit.layout.dimension")

    class FakeDimension:
        def __init__(self, *, preferred: int, min: int, max: int) -> None:
            self.preferred = preferred
            self.min = min
            self.max = max

    setattr(dimension_module, "Dimension", FakeDimension)

    controls_module = ModuleType("prompt_toolkit.layout.controls")
    setattr(controls_module, "FormattedTextControl", lambda fragments: fragments)

    styles_module = ModuleType("prompt_toolkit.styles")
    setattr(
        styles_module,
        "Style",
        SimpleNamespace(from_dict=lambda style_map: style_map),
    )

    widgets_module = ModuleType("prompt_toolkit.widgets")
    widgets_base_module = ModuleType("prompt_toolkit.widgets.base")

    class FakeTextArea:
        def __init__(self, **kwargs) -> None:
            text_area_calls.append(kwargs)
            self.kwargs = kwargs
            self.text = kwargs.get("text", "")

    class FakeBorder:
        TOP_LEFT = "┌"
        TOP_RIGHT = "┐"
        BOTTOM_LEFT = "└"
        BOTTOM_RIGHT = "┘"

    def fake_frame(body, **kwargs):
        frame_calls.append({"body": body, **kwargs})
        return SimpleNamespace(body=body, kwargs=kwargs)

    setattr(widgets_module, "Frame", fake_frame)
    setattr(widgets_module, "TextArea", FakeTextArea)
    setattr(widgets_base_module, "Border", FakeBorder)

    monkeypatch.setitem(sys.modules, "prompt_toolkit", prompt_toolkit_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.application", application_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.key_binding", key_binding_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout", layout_module)
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.layout.containers", containers_module
    )
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.layout.dimension", dimension_module
    )
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout.controls", controls_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.styles", styles_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.widgets", widgets_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.widgets.base", widgets_base_module)

    result = wizard_module._default_prompt_text("Install query", None, large=True)

    assert result == "typed query"
    assert len(frame_calls) == 1
    assert len(text_area_calls) == 1
    assert len(hsplit_calls) == 1
    assert len(vsplit_calls) == 0
    assert "width" not in frame_calls[0]
    assert "width" not in text_area_calls[0]
    assert text_area_calls[0].get("dont_extend_width", False) is False
    assert "width" not in hsplit_calls[0]
    assert ("s-enter",) in binding_calls
    assert ("c-c",) in binding_calls
    footer_fragments = window_calls[1]["args"][0]
    assert "[Shift+Enter] submit  [Ctrl+C] cancel" in footer_fragments[0][1]


def test_default_prompt_text_falls_back_when_shift_enter_binding_is_unsupported(
    monkeypatch,
) -> None:
    binding_calls: list[tuple[object, ...]] = []

    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys, "platform", "linux")

    prompt_toolkit_module = ModuleType("prompt_toolkit")
    setattr(prompt_toolkit_module, "prompt", lambda *_args, **_kwargs: "")

    application_module = ModuleType("prompt_toolkit.application")

    class FakeApplication:
        def __init__(self, **_kwargs) -> None:
            pass

        def run(self) -> str:
            return "typed query"

    setattr(application_module, "Application", FakeApplication)

    key_binding_module = ModuleType("prompt_toolkit.key_binding")

    class FakeKeyBindings:
        def add(self, *keys):
            if keys == ("s-enter",):
                raise ValueError("Invalid key: s-enter")
            binding_calls.append(keys)

            def decorator(func):
                return func

            return decorator

    setattr(key_binding_module, "KeyBindings", FakeKeyBindings)

    layout_module = ModuleType("prompt_toolkit.layout")
    setattr(prompt_toolkit_module, "layout", layout_module)
    setattr(
        layout_module,
        "Layout",
        lambda container, focused_element=None: SimpleNamespace(
            container=container,
            focused_element=focused_element,
        ),
    )

    containers_module = ModuleType("prompt_toolkit.layout.containers")
    setattr(containers_module, "HSplit", lambda children, **_: children)
    setattr(containers_module, "Window", lambda *args, **kwargs: (args, kwargs))

    dimension_module = ModuleType("prompt_toolkit.layout.dimension")

    class FakeDimension:
        def __init__(self, *, preferred: int, min: int, max: int) -> None:
            self.preferred = preferred
            self.min = min
            self.max = max

    setattr(dimension_module, "Dimension", FakeDimension)

    controls_module = ModuleType("prompt_toolkit.layout.controls")
    setattr(controls_module, "FormattedTextControl", lambda fragments: fragments)

    styles_module = ModuleType("prompt_toolkit.styles")
    setattr(
        styles_module,
        "Style",
        SimpleNamespace(from_dict=lambda style_map: style_map),
    )

    widgets_module = ModuleType("prompt_toolkit.widgets")
    widgets_base_module = ModuleType("prompt_toolkit.widgets.base")

    class FakeTextArea:
        def __init__(self, **kwargs) -> None:
            self.text = kwargs.get("text", "")

    class FakeBorder:
        TOP_LEFT = "┌"
        TOP_RIGHT = "┐"
        BOTTOM_LEFT = "└"
        BOTTOM_RIGHT = "┘"

    setattr(widgets_module, "Frame", lambda body, **kwargs: (body, kwargs))
    setattr(widgets_module, "TextArea", FakeTextArea)
    setattr(widgets_base_module, "Border", FakeBorder)

    monkeypatch.setitem(sys.modules, "prompt_toolkit", prompt_toolkit_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.application", application_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.key_binding", key_binding_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout", layout_module)
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.layout.containers", containers_module
    )
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.layout.dimension", dimension_module
    )
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout.controls", controls_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.styles", styles_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.widgets", widgets_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.widgets.base", widgets_base_module)

    result = wizard_module._default_prompt_text("Install query", None, large=True)

    assert result == "typed query"
    assert ("escape", "enter") in binding_calls
    assert ("c-c",) in binding_calls


def test_default_prompt_text_uses_shift_enter_hint_on_macos(monkeypatch) -> None:
    binding_calls: list[tuple[object, ...]] = []
    window_calls: list[WindowCall] = []

    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys, "platform", "darwin")

    prompt_toolkit_module = ModuleType("prompt_toolkit")
    setattr(prompt_toolkit_module, "prompt", lambda *_args, **_kwargs: "")

    application_module = ModuleType("prompt_toolkit.application")

    class FakeApplication:
        def __init__(self, **_kwargs) -> None:
            pass

        def run(self) -> str:
            return "typed query"

    setattr(application_module, "Application", FakeApplication)

    key_binding_module = ModuleType("prompt_toolkit.key_binding")

    class FakeKeyBindings:
        def add(self, *keys):
            binding_calls.append(keys)

            def decorator(func):
                return func

            return decorator

    setattr(key_binding_module, "KeyBindings", FakeKeyBindings)

    layout_module = ModuleType("prompt_toolkit.layout")
    setattr(
        layout_module,
        "Layout",
        lambda container, focused_element=None: SimpleNamespace(
            container=container,
            focused_element=focused_element,
        ),
    )

    containers_module = ModuleType("prompt_toolkit.layout.containers")
    setattr(containers_module, "HSplit", lambda children, **_: children)

    def fake_window(
        *args: list[tuple[str, str]],
        **kwargs: object,
    ) -> SimpleNamespace:
        window_calls.append({"args": args, "kwargs": kwargs})
        return SimpleNamespace(args=args, kwargs=kwargs)

    setattr(containers_module, "Window", fake_window)

    dimension_module = ModuleType("prompt_toolkit.layout.dimension")

    class FakeDimension:
        def __init__(self, *, preferred: int, min: int, max: int) -> None:
            self.preferred = preferred
            self.min = min
            self.max = max

    setattr(dimension_module, "Dimension", FakeDimension)

    controls_module = ModuleType("prompt_toolkit.layout.controls")
    setattr(controls_module, "FormattedTextControl", lambda fragments: fragments)

    styles_module = ModuleType("prompt_toolkit.styles")
    setattr(
        styles_module,
        "Style",
        SimpleNamespace(from_dict=lambda style_map: style_map),
    )

    widgets_module = ModuleType("prompt_toolkit.widgets")
    widgets_base_module = ModuleType("prompt_toolkit.widgets.base")

    class FakeTextArea:
        def __init__(self, **kwargs) -> None:
            self.text = kwargs.get("text", "")

    class FakeBorder:
        TOP_LEFT = "┌"
        TOP_RIGHT = "┐"
        BOTTOM_LEFT = "└"
        BOTTOM_RIGHT = "┘"

    setattr(widgets_module, "Frame", lambda body, **kwargs: (body, kwargs))
    setattr(widgets_module, "TextArea", FakeTextArea)
    setattr(widgets_base_module, "Border", FakeBorder)

    monkeypatch.setitem(sys.modules, "prompt_toolkit", prompt_toolkit_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.application", application_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.key_binding", key_binding_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout", layout_module)
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.layout.containers", containers_module
    )
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.layout.dimension", dimension_module
    )
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout.controls", controls_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.styles", styles_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.widgets", widgets_module)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.widgets.base", widgets_base_module)

    result = wizard_module._default_prompt_text("Install query", None, large=True)

    assert result == "typed query"
    assert ("s-enter",) in binding_calls
    assert ("c-c",) in binding_calls
    footer_fragments = window_calls[1]["args"][0]
    assert "[Shift+Enter] submit  [Ctrl+C] cancel" in footer_fragments[0][1]


def test_default_select_one_prompt_toolkit_scrolls_a_five_row_column_viewport(
    monkeypatch,
) -> None:
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: True)

    prompt_toolkit_application = ModuleType("prompt_toolkit.application")
    captured: dict[str, object] = {}

    class FakeApplication:
        def __init__(self, **kwargs) -> None:
            captured["application_kwargs"] = kwargs

        def run(self) -> str:
            return "project"

    setattr(prompt_toolkit_application, "Application", FakeApplication)

    prompt_toolkit_key_binding = ModuleType("prompt_toolkit.key_binding")
    binding_handlers: dict[tuple[str, ...], Callable[[object], None]] = {}

    class FakeKeyBindings:
        def add(self, *keys):
            def decorator(func):
                binding_handlers[keys] = func
                return func

            return decorator

    setattr(prompt_toolkit_key_binding, "KeyBindings", FakeKeyBindings)

    prompt_toolkit_layout = ModuleType("prompt_toolkit.layout")
    setattr(prompt_toolkit_layout, "Layout", lambda container, **_: container)

    prompt_toolkit_containers = ModuleType("prompt_toolkit.layout.containers")
    setattr(prompt_toolkit_containers, "HSplit", lambda children, **_: children)
    setattr(prompt_toolkit_containers, "Window", lambda control, **_: control)

    prompt_toolkit_controls = ModuleType("prompt_toolkit.layout.controls")

    def fake_formatted_text_control(render_menu, **kwargs):
        captured["control"] = render_menu
        return render_menu

    setattr(
        prompt_toolkit_controls,
        "FormattedTextControl",
        fake_formatted_text_control,
    )

    prompt_toolkit_styles = ModuleType("prompt_toolkit.styles")
    setattr(
        prompt_toolkit_styles,
        "Style",
        SimpleNamespace(from_dict=lambda style_map: style_map),
    )

    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.application", prompt_toolkit_application
    )
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.key_binding", prompt_toolkit_key_binding
    )
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout", prompt_toolkit_layout)
    monkeypatch.setitem(
        sys.modules,
        "prompt_toolkit.layout.containers",
        prompt_toolkit_containers,
    )
    monkeypatch.setitem(
        sys.modules,
        "prompt_toolkit.layout.controls",
        prompt_toolkit_controls,
    )
    monkeypatch.setitem(sys.modules, "prompt_toolkit.styles", prompt_toolkit_styles)

    result = wizard_module._default_select_one(
        "Select candidate",
        [
            *((f"skill-{index}", f"skill-{index}") for index in range(1, 7)),
            ("Return", "__return__"),
        ],
        "Pick a skill.",
        {f"skill-{index}": f"v{index}" for index in range(1, 7)},
        column_header="Skill       Version",
        viewport_size=5,
    )

    render_menu = cast(Callable[[], list[tuple[str, str]]], captured["control"])
    fragments = render_menu()
    assert result == "project"
    rendered = "".join(text for _, text in fragments)
    assert "Skill       Version" in rendered
    divider = "─" * len("Skill       Version")
    assert rendered.index(divider) > rendered.index("Skill       Version")
    assert rendered.index(divider) < rendered.index("skill-1")
    assert "skill-1 v1" in rendered
    assert "skill-5" in rendered
    assert "skill-6" not in rendered
    assert "v2" not in rendered
    assert ("class:column-detail", " v1") in fragments
    assert "↓ 2 more" in rendered
    application_kwargs = cast(dict[str, object], captured["application_kwargs"])
    styles = cast(dict[str, str], application_kwargs["style"])
    assert styles["column-detail"] == "#7a7a7a"

    event = SimpleNamespace(app=SimpleNamespace(invalidate=lambda: None))
    for _ in range(5):
        binding_handlers[("down",)](event)

    rendered = "".join(text for _, text in render_menu())
    assert "skill-1" not in rendered
    assert "skill-6 v6" in rendered
    assert "↑ 1 earlier" in rendered

    binding_handlers[("down",)](event)
    selected: list[str] = []
    binding_handlers[("enter",)](
        SimpleNamespace(
            app=SimpleNamespace(exit=lambda *, result: selected.append(result))
        )
    )
    assert selected == ["__return__"]


def test_default_select_many_prompt_toolkit_shows_toggle_key_hint(monkeypatch) -> None:
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: True)

    prompt_toolkit_application = ModuleType("prompt_toolkit.application")
    captured: dict[str, object] = {}
    binding_handlers: dict[tuple[str, ...], Callable[[object], None]] = {}

    class FakeApplication:
        def __init__(self, **kwargs) -> None:
            captured["application_kwargs"] = kwargs

        def run(self) -> list[str]:
            return ["codex", "cursor"]

    setattr(prompt_toolkit_application, "Application", FakeApplication)

    prompt_toolkit_key_binding = ModuleType("prompt_toolkit.key_binding")
    binding_calls: list[tuple[str, ...]] = []

    class FakeKeyBindings:
        def add(self, *keys):
            binding_calls.append(keys)

            def decorator(func):
                binding_handlers[keys] = func
                return func

            return decorator

    setattr(prompt_toolkit_key_binding, "KeyBindings", FakeKeyBindings)

    prompt_toolkit_layout = ModuleType("prompt_toolkit.layout")
    setattr(prompt_toolkit_layout, "Layout", lambda container, **_: container)

    prompt_toolkit_containers = ModuleType("prompt_toolkit.layout.containers")
    setattr(prompt_toolkit_containers, "HSplit", lambda children, **_: children)
    setattr(prompt_toolkit_containers, "Window", lambda control, **_: control)

    prompt_toolkit_controls = ModuleType("prompt_toolkit.layout.controls")

    def fake_formatted_text_control(render_menu, **kwargs):
        captured["control"] = render_menu
        return render_menu

    setattr(
        prompt_toolkit_controls,
        "FormattedTextControl",
        fake_formatted_text_control,
    )

    prompt_toolkit_styles = ModuleType("prompt_toolkit.styles")
    setattr(
        prompt_toolkit_styles,
        "Style",
        SimpleNamespace(from_dict=lambda style_map: style_map),
    )

    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.application", prompt_toolkit_application
    )
    monkeypatch.setitem(
        sys.modules, "prompt_toolkit.key_binding", prompt_toolkit_key_binding
    )
    monkeypatch.setitem(sys.modules, "prompt_toolkit.layout", prompt_toolkit_layout)
    monkeypatch.setitem(
        sys.modules,
        "prompt_toolkit.layout.containers",
        prompt_toolkit_containers,
    )
    monkeypatch.setitem(
        sys.modules,
        "prompt_toolkit.layout.controls",
        prompt_toolkit_controls,
    )
    monkeypatch.setitem(sys.modules, "prompt_toolkit.styles", prompt_toolkit_styles)

    result = wizard_module._default_select_many(
        "Agent targets",
        [("Codex", "codex"), ("Cursor", "cursor")],
        "Choose one or more agent formats and roots to export into.",
    )

    render_menu = cast(Callable[[], list[tuple[str, str]]], captured["control"])
    fragments = render_menu()
    assert result == ["codex", "cursor"]
    assert ("space",) in binding_calls
    assert ("class:item", "□ ") in fragments
    binding_handlers[("space",)](
        SimpleNamespace(app=SimpleNamespace(invalidate=lambda: None))
    )
    fragments = render_menu()
    assert ("class:marker-active", "■ ") in fragments
    assert fragments[-1] == (
        "class:hint",
        "\n[↑↓] move  [space] select  [enter] confirm  [q] cancel\n\n",
    )


def test_use_rounded_prompt_border_sets_and_restores_corners(monkeypatch) -> None:
    widgets_base_module = ModuleType("prompt_toolkit.widgets.base")

    class FakeBorder:
        TOP_LEFT = "┌"
        TOP_RIGHT = "┐"
        BOTTOM_LEFT = "└"
        BOTTOM_RIGHT = "┘"

    setattr(widgets_base_module, "Border", FakeBorder)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.widgets.base", widgets_base_module)

    with wizard_module._use_rounded_prompt_border():
        assert FakeBorder.TOP_LEFT == "╭"
        assert FakeBorder.TOP_RIGHT == "╮"
        assert FakeBorder.BOTTOM_LEFT == "╰"
        assert FakeBorder.BOTTOM_RIGHT == "╯"

    assert FakeBorder.TOP_LEFT == "┌"
    assert FakeBorder.TOP_RIGHT == "┐"
    assert FakeBorder.BOTTOM_LEFT == "└"
    assert FakeBorder.BOTTOM_RIGHT == "┘"


def test_render_choice_line_marks_active_option_with_filled_bullet() -> None:
    assert wizard_module._render_choice_line("Balanced", active=False) == "○ Balanced"
    assert wizard_module._render_choice_line("Balanced", active=True) == "● Balanced"


def test_render_multi_select_marker_uses_compact_squares() -> None:
    assert wizard_module._render_multi_select_marker(selected=False) == "□"
    assert wizard_module._render_multi_select_marker(selected=True) == "■"


def test_cli_wizard_exits_cleanly_when_selection_is_cancelled() -> None:
    transcript = StringIO()
    wizard = CliWizard(
        workflow_service=FakeWorkflowService(),
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: "postman",
        select_one=lambda *_, **__: (_ for _ in ()).throw(KeyboardInterrupt()),
        confirm=lambda *_, **__: False,
    )

    wizard.run()

    assert "Cancelled." in transcript.getvalue()
