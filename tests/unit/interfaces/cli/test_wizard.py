from __future__ import annotations

import builtins
import sys
from collections.abc import Callable
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Mapping, Sequence, TypedDict, cast

from rich.console import Console

from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    ExecutionPlanDto,
    ExecutionStepDto,
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
    SyncResultDto,
    TraceEntryDto,
)
from aptitude_resolver.domain.errors import DiscoveryNoCandidatesError
from aptitude_resolver.interfaces.cli import wizard as wizard_module
from aptitude_resolver.interfaces.cli.wizard import CliWizard
from aptitude_resolver.telemetry.metrics import StageTiming


class WindowCall(TypedDict):
    args: tuple[list[tuple[str, str]], ...]
    kwargs: dict[str, object]


class FakeWorkflowService:
    def __init__(
        self,
        *,
        resolve_responses: list[ResolveQueryResultDto] | None = None,
        install_responses: list[InstallResultDto] | None = None,
        sync_responses: list[SyncResultDto] | None = None,
    ) -> None:
        self.resolve_responses = list(resolve_responses or [])
        self.install_responses = list(install_responses or [])
        self.sync_responses = list(sync_responses or [])
        self.resolve_calls: list[dict[str, object]] = []
        self.install_calls: list[dict[str, object]] = []
        self.sync_calls: list[dict[str, object]] = []

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
                selection_details=["tokens=120", "size=256B"],
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
                selection_details=["tokens=250", "size=320B"],
                selection_reason="broader match",
            ),
        ],
        trace=[],
    )


def _installed_result(
    materialized_root: str = str(Path("skill_demo")),
) -> InstallResultDto:
    return InstallResultDto(
        requested_query="lint",
        status="installed",
        selection_mode="interactive_choice",
        selected_coordinate=ResolveCoordinateDto(slug="js.lint", version="2.1.0"),
        graph=ResolvedGraphDto(
            root=ResolveCoordinateDto(slug="js.lint", version="2.1.0"),
            nodes=[],
            edges=[],
            install_order=[ResolveCoordinateDto(slug="js.lint", version="2.1.0")],
            conflicts=[],
        ),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="lint",
                requested_version=None,
                selected_node_id="js.lint@2.1.0",
                selection_mode="interactive_choice",
            ),
            nodes=[],
            edges=[],
            install_order=["js.lint@2.1.0"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id="js.lint@2.1.0",
                    skill="js.lint",
                    version="2.1.0",
                    artifact_ref="/skills/js.lint/2.1.0/content",
                    action="materialize_local_skill",
                )
            ]
        ),
        installed_skills=[
            InstalledSkillDto(
                slug="js.lint",
                version="2.1.0",
                install_path=str(
                    Path(materialized_root) / "skills" / "js.lint" / "2.1.0"
                ),
            )
        ],
        materialized_root=materialized_root,
        trace=[],
    )


def _synced_result(
    materialized_root: str = str(Path("skill_demo")),
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
            _selection_required_result(),
            _resolved_result(
                slug="js.lint", version="2.1.0", selection_mode="interactive_choice"
            ),
        ],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["lint"])
    selections = iter(["install", "balanced", "auto", "js.lint"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert len(service.resolve_calls) == 2
    assert service.resolve_calls[1]["select_slug"] == "js.lint"
    assert service.install_calls[0]["query"] == "lint"
    assert service.install_calls[0]["select_slug"] == "js.lint"
    assert "Installation Summary" in transcript.getvalue()


def test_cli_wizard_prints_pipe_separated_install_telemetry() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["python lint"])
    selections = iter(["install", "balanced", "auto"])
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
            confirm=lambda *_, **__: next(confirmations),
        )

        wizard.run()
    finally:
        wizard_module.capture_cli_telemetry = original_capture

    assert "Installation Summary" in transcript.getvalue()
    assert (
        "Install telemetry | Discovery 95.7ms | Materialization 18.2ms"
        in transcript.getvalue()
    )


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
    assert (
        "Aptitude - Review-first CLI for discovering and installing skills." in output
    )
    assert "   ______          __" in output
    assert "wizard launcher" not in output
    assert "[enter] confirm  [↑↓] move  [q] quit" not in output
    assert "Choose a flow" not in output
    assert "Capability Map" not in output


def test_cli_wizard_passes_flow_descriptions_to_selector() -> None:
    transcript = StringIO()
    select_calls: list[dict[str, object]] = []

    def select_one(
        title: str,
        options: Sequence[tuple[str, object]],
        help_text: str | None = None,
        descriptions: Mapping[object, str] | None = None,
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


def test_render_wordmark_supports_alternate_banner_style() -> None:
    rendered = wizard_module._render_wordmark(style="block")

    assert "░▒▓██████▓▒░" in rendered
    assert "Aptitud" not in rendered


def test_format_plan_summary_row_aligns_one_label_value_pair() -> None:
    assert (
        wizard_module._format_plan_summary_row(
            ("Runtime", "unknown"),
        )
        == "Runtime     : unknown"
    )
    assert (
        wizard_module._format_plan_summary_row(
            ("Interaction", "auto"),
        )
        == "Interaction : auto"
    )


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
    assert "Global / framework" in output
    assert 'resolve  aptitude resolve "query" [planning flags]' in output
    assert "--version" in output
    assert "--install-completion" in output
    assert "--show-completion" in output
    assert "aptitude manifest" in output


def test_cli_wizard_can_start_directly_in_install_flow_without_launcher() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["postman primary skill"])
    selections = iter(["balanced", "auto"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run(initial_flow="install")

    output = transcript.getvalue()
    assert "Choose a flow" not in output
    assert service.install_calls[0]["query"] == "postman primary skill"


def test_cli_wizard_can_start_directly_at_install_plan_with_initial_query() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    prompt_calls: list[tuple[str, str | None, bool]] = []
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
        select_one=lambda *_, **__: (_ for _ in ()).throw(
            AssertionError("selection menus should be skipped")
        ),
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run(initial_flow="install", initial_query="postman primary skill")

    output = transcript.getvalue()
    assert "Choose a flow" not in output
    assert prompt_calls == []
    assert service.resolve_calls[0]["query"] == "postman primary skill"
    assert service.install_calls[0]["query"] == "postman primary skill"


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


def test_cli_wizard_uses_large_text_prompt_only_for_install_query() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    prompt_calls: list[tuple[str, str | None, bool]] = []
    answers = iter(["postman primary skill"])
    selections = iter(["install", "balanced", "auto"])
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
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert prompt_calls == [("Install query", None, True)]


def test_cli_wizard_return_from_profile_menu_reopens_query_prompt() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["Postman", "Postman Primary Skill"])
    selections = iter(["install", "__return__", "balanced", "auto"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    assert service.install_calls[0]["query"] == "Postman Primary Skill"


def test_cli_wizard_prints_step_separators_between_install_steps() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )
    transcript = StringIO()
    answers = iter(["postman primary skill"])
    selections = iter(["install", "balanced", "auto"])
    confirmations = iter([True])

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        confirm=lambda *_, **__: next(confirmations),
    )

    wizard.run()

    expected_separator = "─" * 80
    assert transcript.getvalue().count(expected_separator) >= 5


def test_cli_wizard_retries_install_query_after_no_matches() -> None:
    service = FakeWorkflowService(install_responses=[_installed_result()])
    transcript = StringIO()
    answers = iter(["dsas", "postman primary skill"])
    selections = iter(["install", "balanced", "auto", "balanced", "auto"])
    confirmations = iter([True])

    def resolve_query(**kwargs: object) -> ResolveQueryResultDto:
        service.resolve_calls.append(kwargs)
        query = kwargs["query"]
        if query == "dsas":
            raise DiscoveryNoCandidatesError("dsas")
        return _resolved_result()

    wizard = CliWizard(
        workflow_service=service,
        console=Console(file=transcript, force_terminal=False, color_system=None),
        prompt_text=lambda *_, **__: next(answers),
        select_one=lambda *_, **__: next(selections),
        confirm=lambda *_, **__: next(confirmations),
    )
    service.resolve_query = resolve_query  # type: ignore[method-assign]

    wizard.run()

    output = transcript.getvalue()
    assert "No matching skills were found." in output
    assert "Try a more specific query or adjust any restrictive policy flags." in output
    assert service.install_calls[0]["query"] == "postman primary skill"


def test_default_prompt_text_falls_back_to_builtin_input(monkeypatch) -> None:
    monkeypatch.setattr(builtins, "input", lambda _: "postman primary skill")

    assert (
        wizard_module._default_prompt_text("Install query", None)
        == "postman primary skill"
    )


def test_default_select_one_falls_back_to_number_prompt_when_not_a_tty(
    monkeypatch,
) -> None:
    responses = iter(["2"])
    monkeypatch.setattr(builtins, "input", lambda _: next(responses))
    monkeypatch.setattr(wizard_module.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(wizard_module.sys.stdout, "isatty", lambda: False)

    result = wizard_module._default_select_one(
        "Selection profile",
        [("Balanced", "balanced"), ("High trust", "high-trust")],
        "Choose how candidates should be ranked.",
    )

    assert result == "high-trust"


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
    assert ("c-s",) in binding_calls
    assert ("c-a",) in binding_calls
    footer_fragments = window_calls[1]["args"][0]
    assert "[Ctrl+S] submit  [Ctrl+A] cancel" in footer_fragments[0][1]


def test_default_select_one_prompt_toolkit_leaves_blank_line_after_key_hint(
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
            return "auto"

    setattr(prompt_toolkit_application, "Application", FakeApplication)

    prompt_toolkit_key_binding = ModuleType("prompt_toolkit.key_binding")

    class FakeKeyBindings:
        def add(self, *_keys):
            def decorator(func):
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
        "Interaction mode",
        [("Auto", "auto"), ("Always ask", "always")],
        "Choose how ambiguity should be handled.",
    )

    render_menu = cast(Callable[[], list[tuple[str, str]]], captured["control"])
    fragments = render_menu()
    assert result == "auto"
    assert fragments[-1] == (
        "class:hint",
        "\n[↑↓] move  [enter] confirm  [q] cancel\n\n",
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
