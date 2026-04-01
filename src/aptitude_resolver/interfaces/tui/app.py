"""Full-screen Textual aptitude_resolver for guided Aptitude installs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Select, Static

from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    InstallResultDto,
    ResolveQueryResultDto,
)
from aptitude_resolver.domain.errors import AptitudeResolverError
from aptitude_resolver.interfaces.shared import (
    InstallWorkflowOptions,
    InstallWorkflowService,
    InteractionMode,
)


PROFILE_OPTIONS = [
    ("Balanced", "balanced"),
    ("Low cost", "low-cost"),
    ("High trust", "high-trust"),
]

INTERACTION_OPTIONS = [
    ("Auto", "auto"),
    ("Always ask", "always"),
    ("Never ask", "never"),
]


@dataclass
class InstallSessionState:
    """Persistent UI state shared across TUI screens."""

    query: str = ""
    selection_profile: str = "balanced"
    interaction_mode: InteractionMode = "auto"
    target: Path = Path("skill_demo")
    selected_slug: str | None = None
    resolve_result: ResolveQueryResultDto | None = None


def _render_error(error: AptitudeResolverError) -> str:
    """Render the same structured error payload used by the CLI."""

    return json.dumps({"error": error.to_payload()}, indent=2)


def _render_candidate(candidate: DiscoveryCandidateDto, *, index: int) -> str:
    """Render one candidate choice for the selector screen."""

    details = ", ".join(candidate.selection_details or [])
    reason = candidate.selection_reason or "Ranked by Aptitude policy and matching."
    return (
        f"{index}. {candidate.name}\n"
        f"{candidate.slug}@{candidate.version} | {candidate.runtime or 'unknown runtime'} | "
        f"{candidate.trust_tier} | {candidate.lifecycle_status}\n"
        f"{candidate.description}\n"
        f"{details}\n"
        f"{reason}"
    )


def _render_plan_summary(
    result: ResolveQueryResultDto,
    *,
    selection_profile: str,
    interaction_mode: InteractionMode,
    target: Path,
) -> str:
    """Render one operator-style plan summary for the review screen."""

    selected = result.selected_coordinate
    assert selected is not None
    assert result.execution_plan is not None
    assert result.graph is not None
    selected_skill = result.selected_skill
    runtime = (
        selected_skill.runtime if selected_skill is not None else "unknown runtime"
    )
    trust = selected_skill.trust_tier if selected_skill is not None else "unknown"
    lifecycle = (
        selected_skill.lifecycle_status if selected_skill is not None else "unknown"
    )
    step_lines = "\n".join(
        f"  {index}. {step.skill}@{step.version} -> {step.action}"
        for index, step in enumerate(result.execution_plan.steps, start=1)
    )
    return (
        f"Selected skill : {selected.slug}@{selected.version}\n"
        f"Runtime        : {runtime}\n"
        f"Trust/Lifecycle: {trust} / {lifecycle}\n"
        f"Selection mode : {result.selection_mode}\n"
        f"Policy profile : {selection_profile}\n"
        f"Interaction    : {interaction_mode}\n"
        f"Target path    : {target}\n"
        f"Graph nodes    : {len(result.graph.nodes)}\n"
        f"Plan steps     : {len(result.execution_plan.steps)}\n\n"
        f"Execution plan\n{step_lines}"
    )


def _render_install_result(result: InstallResultDto) -> str:
    """Render the final install result for the success screen."""

    installed = (
        ", ".join(f"{skill.slug}@{skill.version}" for skill in result.installed_skills)
        or "No skills materialized."
    )
    root = result.materialized_root or "No local materialization root returned."
    return (
        "Successfully installed the selected skill graph.\n\n"
        f"Installed skills: {installed}\n"
        f"Materialized at : {root}"
    )


def _installer_app(screen: Screen) -> "AptitudeInstallerApp":
    """Return the concrete installer aptitude_resolver controller for a screen."""

    return cast("AptitudeInstallerApp", screen.app)


class QueryScreen(Screen):
    """Collect the initial query and core policy controls."""

    def __init__(self, state: InstallSessionState) -> None:
        super().__init__(name="query")
        self._state = state

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="surface"):
            with Vertical(classes="panel"):
                yield Static("APTITUDE // install operator", classes="chrome")
                yield Static("APTITUDE", id="hero")
                yield Static(
                    "Skill install operator\nReview the plan before any local materialization.",
                    id="hero-copy",
                )
                yield Input(
                    value=self._state.query,
                    placeholder="Describe the skill you want to install",
                    id="query-input",
                )
                yield Select(
                    PROFILE_OPTIONS,
                    value=self._state.selection_profile,
                    allow_blank=False,
                    id="profile-select",
                )
                yield Select(
                    INTERACTION_OPTIONS,
                    value=self._state.interaction_mode,
                    allow_blank=False,
                    id="interaction-select",
                )
                yield Static(
                    "Review the plan, inspect candidates if needed, then install.",
                    id="query-status",
                )
                with Horizontal(classes="button-row"):
                    yield Button(
                        "Review plan", id="review-plan-button", variant="primary"
                    )
                yield Static(
                    "Ctrl+C quits. Buttons drive the flow.", classes="footer-hint"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Start the resolve flow from the form state."""

        if event.button.id != "review-plan-button":
            return

        query_input = self.query_one("#query-input", Input)
        query = query_input.value.strip()
        if not query:
            self.query_one("#query-status", Static).update(
                "Enter a query before reviewing."
            )
            return

        profile_select = self.query_one("#profile-select", Select)
        interaction_select = self.query_one("#interaction-select", Select)
        self._state.query = query
        self._state.selection_profile = str(profile_select.value)
        self._state.interaction_mode = cast(InteractionMode, interaction_select.value)
        self._state.selected_slug = None
        self._state.resolve_result = None
        _installer_app(self).begin_review()


class CandidateScreen(Screen):
    """Let the user choose among ambiguous candidates."""

    def __init__(
        self,
        state: InstallSessionState,
        result: ResolveQueryResultDto,
    ) -> None:
        super().__init__(name="candidate")
        self._state = state
        self._result = result

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="surface"):
            with Vertical(classes="panel"):
                yield Static("APTITUDE // candidate review", classes="chrome")
                yield Static("Resolve ambiguity", classes="section-title")
                yield Static(
                    "Multiple candidates match the query. Pick one to continue to the install plan.",
                    classes="section-copy",
                )
                for index, candidate in enumerate(self._result.candidates, start=1):
                    yield Button(
                        _render_candidate(candidate, index=index),
                        id=f"candidate-{index}",
                        classes="candidate-button",
                    )
                with Horizontal(classes="button-row"):
                    yield Button("Back", id="candidate-back-button")
                yield Static("Back returns to the query form.", classes="footer-hint")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle candidate selection or navigation back to the query form."""

        button_id = event.button.id or ""
        if button_id == "candidate-back-button":
            _installer_app(self).show_query_screen()
            return
        if not button_id.startswith("candidate-"):
            return

        index = int(button_id.split("-")[-1]) - 1
        selected = self._result.candidates[index]
        self._state.selected_slug = selected.slug
        _installer_app(self).begin_review(
            select_slug=selected.slug, selection_source="interactive"
        )


class PlanScreen(Screen):
    """Show the selected plan before materialization."""

    def __init__(
        self,
        state: InstallSessionState,
        result: ResolveQueryResultDto,
    ) -> None:
        super().__init__(name="plan")
        self._state = state
        self._result = result

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="surface"):
            with Vertical(classes="panel"):
                yield Static("APTITUDE // plan review", classes="chrome")
                yield Static("Install plan", classes="section-title")
                yield Static(
                    _render_plan_summary(
                        self._result,
                        selection_profile=self._state.selection_profile,
                        interaction_mode=self._state.interaction_mode,
                        target=self._state.target,
                    ),
                    id="plan-summary",
                )
                with Horizontal(classes="button-row"):
                    yield Button("Back", id="plan-back-button")
                    yield Button("Install", id="install-button", variant="primary")
                yield Static("Review first, then materialize.", classes="footer-hint")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route plan actions to the application controller."""

        if event.button.id == "plan-back-button":
            _installer_app(self).show_query_screen()
            return
        if event.button.id == "install-button":
            _installer_app(self).begin_install()


class ProgressScreen(Screen):
    """Display threaded workflow progress."""

    def __init__(self, title: str, messages: list[str]) -> None:
        super().__init__(name="progress")
        self._title = title
        self._messages = messages

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="surface"):
            with Vertical(classes="panel"):
                yield Static("APTITUDE // progress", classes="chrome")
                yield Static(self._title, classes="section-title")
                yield Static("\n".join(self._messages), id="progress-status")
                yield Static("Working in the background thread.", classes="footer-hint")

    def update_messages(self, messages: list[str]) -> None:
        """Replace the progress log on screen."""

        self._messages = list(messages)
        self.query_one("#progress-status", Static).update("\n".join(self._messages))


class ResultScreen(Screen):
    """Show either a success or an error result."""

    def __init__(self, *, title: str, summary: str, error: bool = False) -> None:
        super().__init__(name="result")
        self._title = title
        self._summary = summary
        self._error = error

    def compose(self) -> ComposeResult:
        summary_id = "error-summary" if self._error else "result-summary"
        with VerticalScroll(id="surface"):
            with Vertical(classes="panel"):
                yield Static("APTITUDE // result", classes="chrome")
                yield Static(self._title, classes="section-title")
                yield Static(self._summary, id=summary_id)
                with Horizontal(classes="button-row"):
                    yield Button("Start over", id="restart-button", variant="primary")
                yield Static(
                    "Start over returns to the query form.", classes="footer-hint"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reset the flow from the final screen."""

        if event.button.id == "restart-button":
            _installer_app(self).show_query_screen()


class WorkflowServicePort(Protocol):
    def resolve_query(
        self,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
        options: InstallWorkflowOptions | None = None,
    ) -> ResolveQueryResultDto: ...

    def install_query(
        self,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        target: Path,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
        options: InstallWorkflowOptions | None = None,
    ) -> InstallResultDto: ...


class AptitudeInstallerApp(App[None]):
    """Guided Textual install experience for Aptitude."""

    CSS = """
    Screen {
        background: #0a1016;
        color: #dce7f2;
    }

    Header {
        background: #101925;
        color: #7dd3fc;
    }

    Footer {
        background: #101925;
        color: #8ba4bd;
    }

    #surface {
        padding: 1 2;
    }

    .panel {
        width: 1fr;
        max-width: 110;
        min-height: 16;
        padding: 1 2;
        border: wide #274863;
        background: #111b27;
    }

    #hero {
        color: #f8fafc;
        text-style: bold;
        margin-bottom: 1;
    }

    .chrome {
        color: #7dd3fc;
        text-style: bold;
        margin-bottom: 1;
    }

    #hero-copy, .section-copy, #query-status {
        color: #9db0c3;
        margin-bottom: 1;
    }

    .section-title {
        color: #7dd3fc;
        text-style: bold;
        margin-bottom: 1;
    }

    Input, Select, Button {
        margin-bottom: 1;
    }

    .candidate-button {
        height: auto;
        min-height: 5;
        content-align: left middle;
        text-align: left;
        background: #162332;
        border: solid #22384d;
        color: #dce7f2;
    }

    .candidate-button:hover {
        border: solid #3b82f6;
    }

    .button-row {
        height: auto;
        align-horizontal: right;
    }

    .footer-hint {
        color: #7891a8;
        margin-top: 1;
    }

    #plan-summary, #progress-status, #result-summary, #error-summary {
        background: #0d151f;
        border: tall #1f3447;
        padding: 1 2;
        margin-bottom: 1;
        height: auto;
    }

    #error-summary {
        color: #fecaca;
        border: tall #7f1d1d;
    }
    """

    TITLE = "Aptitude"
    SUB_TITLE = "Install skills"

    def __init__(
        self,
        *,
        workflow_service: WorkflowServicePort | None = None,
        default_target: Path = Path("skill_demo"),
    ) -> None:
        super().__init__()
        self._workflow_service = workflow_service or InstallWorkflowService()
        self._state = InstallSessionState(target=default_target)
        self._progress_title = "Working"
        self._progress_messages: list[str] = []

    def on_mount(self) -> None:
        """Open the initial query screen."""

        self.push_screen(QueryScreen(self._state))

    def show_query_screen(self) -> None:
        """Return to the query form."""

        while not isinstance(self.screen, QueryScreen):
            self.pop_screen()

    def show_candidate_screen(self, result: ResolveQueryResultDto) -> None:
        """Open the candidate selector."""

        self._pop_progress_screen()
        self._pop_review_screen()
        self.push_screen(CandidateScreen(self._state, result))

    def show_plan_screen(self, result: ResolveQueryResultDto) -> None:
        """Open the plan review screen."""

        self._pop_progress_screen()
        self._pop_review_screen()
        self.push_screen(PlanScreen(self._state, result))

    def show_progress_screen(self, title: str, message: str) -> None:
        """Open the progress screen with one initial status line."""

        self._progress_title = title
        self._progress_messages = [message]
        self.push_screen(ProgressScreen(title, self._progress_messages))

    def append_progress(self, message: str) -> None:
        """Append a status line to the progress screen."""

        self._progress_messages.append(message)
        if isinstance(self.screen, ProgressScreen):
            self.screen.update_messages(self._progress_messages)

    def show_result_screen(self, result: InstallResultDto) -> None:
        """Open the final success screen."""

        self._pop_progress_screen()
        self._pop_review_screen()
        self.push_screen(
            ResultScreen(
                title="Install complete",
                summary=_render_install_result(result),
            )
        )

    def show_error_screen(self, error: AptitudeResolverError) -> None:
        """Open the structured error screen."""

        self._pop_progress_screen()
        self._pop_review_screen()
        self.push_screen(
            ResultScreen(
                title="Install blocked",
                summary=_render_error(error),
                error=True,
            )
        )

    def _build_options(self) -> InstallWorkflowOptions:
        """Create workflow options from the current UI state."""

        return InstallWorkflowOptions(
            selection_profile=self._state.selection_profile,
            interaction_mode=self._state.interaction_mode,
        )

    def _pop_progress_screen(self) -> None:
        """Remove the transient progress screen when it is on top."""

        if isinstance(self.screen, ProgressScreen):
            self.pop_screen()

    def _pop_review_screen(self) -> None:
        """Remove transient review screens so the next overlay replaces them."""

        if isinstance(self.screen, (CandidateScreen, PlanScreen, ResultScreen)):
            self.pop_screen()

    def begin_review(
        self,
        *,
        select_slug: str | None = None,
        selection_source: str | None = None,
    ) -> None:
        """Kick off query resolution in a worker thread."""

        self.show_progress_screen(
            "Reviewing plan", "Resolving query against the registry."
        )
        self.resolve_query_worker(
            select_slug=select_slug,
            selection_source=selection_source,
        )

    def begin_install(self) -> None:
        """Kick off installation in a worker thread."""

        self.show_progress_screen("Installing", "Preparing local materialization.")
        self.install_query_worker()

    @work(thread=True, exclusive=True, group="resolve", exit_on_error=False)
    def resolve_query_worker(
        self,
        *,
        select_slug: str | None,
        selection_source: str | None,
    ) -> None:
        """Resolve the current query without blocking the UI thread."""

        self.call_from_thread(
            self.append_progress,
            "Applying current profile and interaction settings.",
        )
        try:
            result = self._workflow_service.resolve_query(
                query=self._state.query,
                version=None,
                select_slug=select_slug,
                interaction_mode="never" if selection_source is not None else None,
                prompt_capable=False,
                selection_source=selection_source,
                options=self._build_options(),
            )
        except AptitudeResolverError as error:
            self.call_from_thread(self.show_error_screen, error)
            return

        self.call_from_thread(self._handle_resolve_result, result, select_slug)

    @work(thread=True, exclusive=True, group="install", exit_on_error=False)
    def install_query_worker(self) -> None:
        """Install the selected query without blocking the UI thread."""

        self.call_from_thread(
            self.append_progress, "Materializing the selected skill graph."
        )
        try:
            result = self._workflow_service.install_query(
                query=self._state.query,
                version=None,
                select_slug=self._state.selected_slug,
                target=self._state.target,
                interaction_mode=None,
                prompt_capable=False,
                selection_source="textual",
                options=self._build_options(),
            )
        except AptitudeResolverError as error:
            self.call_from_thread(self.show_error_screen, error)
            return

        self.call_from_thread(
            self.append_progress,
            f"Installed {len(result.installed_skills)} skills into the workspace.",
        )
        self.call_from_thread(self.show_result_screen, result)

    def _handle_resolve_result(
        self,
        result: ResolveQueryResultDto,
        select_slug: str | None,
    ) -> None:
        """Route the resolve result to the next guided screen."""

        if result.status == "selection_required":
            self.show_candidate_screen(result)
            return

        self._state.selected_slug = select_slug or (
            result.selected_coordinate.slug
            if result.selected_coordinate is not None
            else None
        )
        self._state.resolve_result = result
        self.show_plan_screen(result)


def run_tui_app() -> None:
    """Launch the Textual Aptitude installer."""

    AptitudeInstallerApp().run()
