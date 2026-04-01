"""Full-screen Textual installer for guided Aptitude installs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Select, Static

from aptitude.application.dto import (
    DiscoveryCandidateDto,
    InstallResultDto,
    ResolveQueryResultDto,
)
from aptitude.domain.errors import AptitudeResolverError
from aptitude.interfaces.shared import (
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


try:
    from textual import widgets as textual_widgets
except ImportError:  # pragma: no cover - Textual is a required dependency.
    textual_widgets = None


MEDIA_WIDGET_AVAILABLE = bool(
    textual_widgets is not None and hasattr(textual_widgets, "Image")
)


@dataclass
class InstallSessionState:
    """Persistent UI state shared across TUI screens."""

    query: str = ""
    selection_profile: str = "balanced"
    interaction_mode: InteractionMode = "auto"
    target: Path = Path("skill_demo")
    selected_slug: str | None = None
    resolve_result: ResolveQueryResultDto | None = None


class QueryInput(Input):
    """Query input that reserves the global quit shortcut."""

    def check_consume_key(self, key: str, character: str | None) -> bool:
        """Let the app-level quit binding handle lowercase q."""

        if key == "q":
            return False
        return super().check_consume_key(key, character)


def _format_runtime(runtime: str | None) -> str:
    """Normalize one optional runtime label for display."""

    return runtime or "unknown runtime"


def _render_error(error: AptitudeResolverError) -> str:
    """Render one human-first error summary with structured details."""

    payload = json.dumps({"error": error.to_payload()}, indent=2)
    return (
        "Aptitude blocked the install before local materialization.\n\n"
        f"{error.__class__.__name__}\n\n"
        "Structured details\n"
        f"{payload}"
    )


def _render_query_context(state: InstallSessionState) -> str:
    """Summarize the current install posture before execution."""

    return (
        f"Selection profile : {state.selection_profile}\n"
        f"Interaction mode  : {state.interaction_mode}\n"
        f"Target path       : {state.target}\n"
        "Safety posture    : review first, materialize second"
    )


def _discover_media_asset() -> Path | None:
    """Return one optional operator-provided media asset path."""

    raw_path = os.getenv("APTITUDE_TUI_MEDIA")
    if not raw_path:
        return None
    candidate = Path(raw_path).expanduser()
    return candidate if candidate.exists() else None


def _render_media_copy() -> str:
    """Describe the current media posture without depending on images."""

    asset = _discover_media_asset()
    if asset is None:
        return (
            "Media stays optional.\n"
            "No reference asset is loaded, so this surface stays clean and text-first."
        )
    if MEDIA_WIDGET_AVAILABLE:
        return (
            f"Reference asset ready: {asset.name}\n"
            "This terminal can render inline media, but the layout still works without it."
        )
    return (
        f"Reference asset detected: {asset.name}\n"
        "This terminal cannot render inline images, so Aptitude falls back to the "
        "minimal text surface."
    )


def _render_candidate_reason(candidate: DiscoveryCandidateDto) -> str:
    """Render one concise ranking explanation for a candidate card."""

    return candidate.selection_reason or "Ranked by Aptitude policy and skill matching."


def _render_candidate_details(candidate: DiscoveryCandidateDto) -> str:
    """Render one compact detail row for a candidate card."""

    details = list(candidate.selection_details)
    if not details:
        details.append(f"published={candidate.published_at}")
    return " | ".join(details)


def _render_plan_overview(result: ResolveQueryResultDto) -> str:
    """Render the selected-skill overview for plan review."""

    selected = result.selected_coordinate
    assert selected is not None
    skill = result.selected_skill
    title = skill.name if skill is not None else selected.slug
    summary = (
        skill.rendered_summary
        if skill is not None
        else "Selection resolved and ready for review."
    )
    description = skill.description if skill is not None else ""
    lines = [title, f"{selected.slug}@{selected.version}", summary]
    if description and description != summary:
        lines.append(description)
    return "\n".join(lines)


def _render_plan_metadata(
    result: ResolveQueryResultDto,
    *,
    selection_profile: str,
    interaction_mode: InteractionMode,
    target: Path,
) -> str:
    """Render plan-level metadata for the review screen."""

    selected = result.selected_coordinate
    assert selected is not None
    assert result.execution_plan is not None
    assert result.graph is not None
    skill = result.selected_skill
    trust = skill.trust_tier if skill is not None else "unknown"
    lifecycle = skill.lifecycle_status if skill is not None else "unknown"
    runtime = _format_runtime(skill.runtime if skill is not None else None)
    return (
        f"Selected skill : {selected.slug}@{selected.version}\n"
        f"Runtime        : {runtime}\n"
        f"Trust/Lifecycle: {trust} / {lifecycle}\n"
        f"Selection mode : {result.selection_mode}\n"
        f"Policy profile : {selection_profile}\n"
        f"Interaction    : {interaction_mode}\n"
        f"Target path    : {target}\n"
        f"Graph nodes    : {len(result.graph.nodes)}\n"
        f"Plan steps     : {len(result.execution_plan.steps)}"
    )


def _render_plan_steps(result: ResolveQueryResultDto) -> str:
    """Render the execution plan as a compact checklist."""

    assert result.execution_plan is not None
    return "\n".join(
        f"{index}. {step.skill}@{step.version} -> {step.action}"
        for index, step in enumerate(result.execution_plan.steps, start=1)
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


def _render_progress_log(messages: list[str]) -> str:
    """Render one readable progress log."""

    return "\n".join(f"- {message}" for message in messages)


def _installer_app(screen: Screen) -> "AptitudeInstallerApp":
    """Return the concrete installer controller for a screen."""

    return cast("AptitudeInstallerApp", screen.app)


def _meta_chip(text: str, *, id: str | None = None, tone: str = "neutral") -> Static:
    """Create one consistently styled metadata chip."""

    return Static(text, id=id, classes=f"meta-chip {tone}")


def _header_widgets(title: str, copy: str) -> tuple[Static, Static, Static]:
    """Build a consistent framed header for one screen."""

    return (
        Static("APTITUDE", classes="eyebrow"),
        Static(title, classes="page-title"),
        Static(copy, classes="page-copy"),
    )


def _render_shortcut_bar(*items: tuple[str, str]) -> str:
    """Render one compact shortcut menu."""

    return "  |  ".join(f"[{key}] {label}" for key, label in items)


def _focus_button_offset(screen: Screen, offset: int) -> None:
    """Move button focus relative to the currently focused button."""

    buttons = list(screen.query(Button))
    if not buttons:
        return

    focused = screen.app.focused
    current_index = 0
    if isinstance(focused, Button):
        try:
            current_index = buttons.index(focused)
        except ValueError:
            current_index = 0

    buttons[(current_index + offset) % len(buttons)].focus()


class QueryScreen(Screen):
    """Collect the initial query and core policy controls."""

    def __init__(self, state: InstallSessionState) -> None:
        super().__init__(name="query")
        self._state = state

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="surface"):
            with Vertical(classes="surface-frame"):
                with Vertical(classes="screen-header card card-shell"):
                    for widget in _header_widgets(
                        "Install skills with a review-first flow",
                        "Resolve a request, inspect the plan, then materialize with predictable steps.",
                    ):
                        yield widget
                with Vertical(id="query-card", classes="card card-primary"):
                    yield Static("Install query", classes="card-title")
                    yield Static(
                        "Describe the skill or capability you want. Aptitude reviews the plan before writing anything locally.",
                        classes="card-copy",
                    )
                    yield QueryInput(
                        value=self._state.query,
                        placeholder="Describe the skill you want to install",
                        id="query-input",
                    )
                    yield Static("Selection profile", classes="field-label")
                    yield Select(
                        PROFILE_OPTIONS,
                        value=self._state.selection_profile,
                        allow_blank=False,
                        id="profile-select",
                    )
                    yield Static("Interaction mode", classes="field-label")
                    yield Select(
                        INTERACTION_OPTIONS,
                        value=self._state.interaction_mode,
                        allow_blank=False,
                        id="interaction-select",
                    )
                    yield Static(
                        "Review the plan, inspect candidates if needed, then install.",
                        id="query-status",
                        classes="status-note",
                    )
                    with Horizontal(classes="button-row"):
                        yield Button(
                            "Review plan", id="review-plan-button", variant="primary"
                        )
                with Horizontal(classes="card-grid"):
                    with Vertical(id="context-card", classes="card card-secondary grid-card"):
                        yield Static("Install posture", classes="card-title")
                        yield Static(
                            _render_query_context(self._state),
                            id="query-context",
                            classes="card-copy",
                        )
                    with Vertical(id="media-card", classes="card card-secondary grid-card"):
                        yield Static("Inspiration", classes="card-title")
                        yield Static(
                            _render_media_copy(),
                            id="hero-media",
                            classes="card-copy",
                        )
                yield Static(
                    _render_shortcut_bar(
                        ("Enter", "review plan"),
                        ("Tab", "next control"),
                        ("Shift+Tab", "previous"),
                        ("Q", "quit"),
                    ),
                    classes="nav-strip",
                )

    def on_mount(self) -> None:
        """Put focus on the query input when the screen opens."""

        self.call_after_refresh(self._focus_query_input)

    def _focus_query_input(self) -> None:
        """Focus the query input after the layout settles."""

        self.query_one("#query-input", Input).focus()

    def submit_review(self) -> None:
        """Start the resolve flow from the form state."""

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route the review button to the shared submit flow."""

        if event.button.id == "review-plan-button":
            self.submit_review()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Treat Enter inside the query input as the primary action."""

        if event.input.id == "query-input":
            self.submit_review()


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
            with Vertical(classes="surface-frame"):
                with Vertical(classes="screen-header card card-shell"):
                    for widget in _header_widgets(
                        "Choose the closest match",
                        "Multiple candidates satisfy the query. Pick the one that best matches the intent before installing.",
                    ):
                        yield widget
                for index, candidate in enumerate(self._result.candidates, start=1):
                    with Vertical(
                        id=f"candidate-card-{index}",
                        classes="card candidate-card",
                    ):
                        yield Static(candidate.name, classes="candidate-title")
                        yield Static(
                            f"{candidate.slug}@{candidate.version}",
                            classes="candidate-slug",
                        )
                        with Horizontal(classes="meta-row"):
                            yield _meta_chip(
                                _format_runtime(candidate.runtime),
                                id=f"candidate-runtime-{index}",
                                tone="accent",
                            )
                            yield _meta_chip(
                                candidate.trust_tier,
                                id=f"candidate-trust-{index}",
                            )
                            yield _meta_chip(
                                candidate.lifecycle_status,
                                id=f"candidate-lifecycle-{index}",
                            )
                            yield _meta_chip(
                                f"rank #{candidate.ranking_position}",
                                id=f"candidate-rank-{index}",
                                tone="muted",
                            )
                        yield Static(candidate.description, classes="candidate-copy")
                        yield Static(
                            _render_candidate_reason(candidate),
                            id=f"candidate-reason-{index}",
                            classes="candidate-reason",
                        )
                        yield Static(
                            _render_candidate_details(candidate),
                            id=f"candidate-details-{index}",
                            classes="candidate-details",
                        )
                        with Horizontal(classes="button-row"):
                            yield Button(
                                "Choose candidate",
                                id=f"candidate-{index}",
                                variant="primary" if index == 1 else "default",
                            )
                with Horizontal(classes="button-row"):
                    yield Button("Back", id="candidate-back-button")
                yield Static(
                    _render_shortcut_bar(
                        ("Up/Down", "move candidates"),
                        ("Tab", "cycle actions"),
                        ("Enter", "choose focused"),
                        ("Esc", "back"),
                        ("Q", "quit"),
                    ),
                    classes="nav-strip",
                )

    def on_mount(self) -> None:
        """Focus the first candidate action for keyboard-first selection."""

        self.call_after_refresh(self._focus_first_candidate)

    def _focus_first_candidate(self) -> None:
        """Focus the first candidate button after layout."""

        self.query_one("#candidate-1", Button).focus()

    def go_back(self) -> None:
        """Return to the query screen without selecting a candidate."""

        _installer_app(self).show_query_screen()

    def _select_candidate(self, button_id: str) -> None:
        """Select one candidate and restart the review flow."""

        index = int(button_id.split("-")[-1]) - 1
        selected = self._result.candidates[index]
        self._state.selected_slug = selected.slug
        _installer_app(self).begin_review(
            select_slug=selected.slug,
            selection_source="interactive",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle candidate selection or navigation back to the query form."""

        button_id = event.button.id or ""
        if button_id == "candidate-back-button":
            self.go_back()
            return
        if button_id.startswith("candidate-"):
            self._select_candidate(button_id)

    def on_key(self, event: events.Key) -> None:
        """Handle review-stage shortcuts for the candidate screen."""

        if event.key == "escape":
            self.go_back()
            event.stop()
            event.prevent_default()
        elif event.key in {"up", "left"}:
            _focus_button_offset(self, -1)
            event.stop()
            event.prevent_default()
        elif event.key in {"down", "right"}:
            _focus_button_offset(self, 1)
            event.stop()
            event.prevent_default()
        elif event.key == "q":
            self.app.exit()
            event.stop()
            event.prevent_default()


class PlanScreen(Screen):
    """Show the selected install plan before materialization."""

    def __init__(
        self,
        state: InstallSessionState,
        result: ResolveQueryResultDto,
    ) -> None:
        super().__init__(name="plan")
        self._state = state
        self._result = result

    def compose(self) -> ComposeResult:
        selected_skill = self._result.selected_skill
        with VerticalScroll(id="surface"):
            with Vertical(classes="surface-frame"):
                with Vertical(classes="screen-header card card-shell"):
                    for widget in _header_widgets(
                        "Inspect before install",
                        "Review the selected skill, execution context, and steps before materializing anything.",
                    ):
                        yield widget
                with Horizontal(classes="card-grid"):
                    with Vertical(id="overview-card", classes="card card-primary grid-card"):
                        yield Static("Selected skill", classes="card-title")
                        yield Static(
                            _render_plan_overview(self._result),
                            id="plan-overview",
                            classes="card-copy",
                        )
                        with Horizontal(classes="meta-row"):
                            yield _meta_chip(
                                _format_runtime(
                                    selected_skill.runtime if selected_skill is not None else None
                                ),
                                tone="accent",
                            )
                            if selected_skill is not None:
                                yield _meta_chip(selected_skill.trust_tier)
                                yield _meta_chip(selected_skill.lifecycle_status)
                    with Vertical(id="metadata-card", classes="card card-secondary grid-card"):
                        yield Static("Execution context", classes="card-title")
                        yield Static(
                            _render_plan_metadata(
                                self._result,
                                selection_profile=self._state.selection_profile,
                                interaction_mode=self._state.interaction_mode,
                                target=self._state.target,
                            ),
                            id="plan-metadata",
                            classes="card-copy",
                        )
                with Vertical(id="steps-card", classes="card card-secondary"):
                    yield Static("Execution steps", classes="card-title")
                    yield Static(
                        _render_plan_steps(self._result),
                        id="plan-steps",
                        classes="card-copy",
                    )
                with Horizontal(classes="button-row"):
                    yield Button("Back", id="plan-back-button")
                    yield Button("Install", id="install-button", variant="primary")
                yield Static(
                    _render_shortcut_bar(
                        ("Left/Right", "move actions"),
                        ("Enter", "press focused"),
                        ("I", "install now"),
                        ("Esc", "back"),
                        ("Q", "quit"),
                    ),
                    classes="nav-strip",
                )

    def on_mount(self) -> None:
        """Focus the primary action when the plan screen opens."""

        self.call_after_refresh(self._focus_install_button)

    def _focus_install_button(self) -> None:
        """Focus the install button after layout."""

        self.query_one("#install-button", Button).focus()

    def go_back(self) -> None:
        """Return to the query screen."""

        _installer_app(self).show_query_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route plan actions to the application controller."""

        if event.button.id == "plan-back-button":
            self.go_back()
            return
        if event.button.id == "install-button":
            _installer_app(self).begin_install()

    def on_key(self, event: events.Key) -> None:
        """Handle plan-stage keyboard shortcuts."""

        if event.key == "escape":
            self.go_back()
            event.stop()
            event.prevent_default()
        elif event.key in {"left", "up"}:
            _focus_button_offset(self, -1)
            event.stop()
            event.prevent_default()
        elif event.key in {"right", "down"}:
            _focus_button_offset(self, 1)
            event.stop()
            event.prevent_default()
        elif event.key == "i":
            _installer_app(self).begin_install()
            event.stop()
            event.prevent_default()
        elif event.key == "q":
            self.app.exit()
            event.stop()
            event.prevent_default()


class ProgressScreen(Screen):
    """Display threaded workflow progress."""

    def __init__(self, title: str, messages: list[str]) -> None:
        super().__init__(name="progress")
        self._title = title
        self._messages = messages

    def compose(self) -> ComposeResult:
        latest = self._messages[-1] if self._messages else "Working."
        with VerticalScroll(id="surface"):
            with Vertical(classes="surface-frame"):
                with Vertical(classes="screen-header card card-shell"):
                    for widget in _header_widgets(
                        self._title,
                        "Aptitude is working in a background thread. The log below updates as the install progresses.",
                    ):
                        yield widget
                with Vertical(classes="card card-primary"):
                    yield Static("Current step", classes="card-title")
                    yield Static(latest, id="progress-latest", classes="card-copy")
                with Vertical(classes="card card-secondary"):
                    yield Static("Progress log", classes="card-title")
                    yield Static(
                        _render_progress_log(self._messages),
                        id="progress-status",
                        classes="card-copy",
                    )
                yield Static(
                    _render_shortcut_bar(("Status", "background work in progress")),
                    classes="nav-strip",
                )

    def update_messages(self, messages: list[str]) -> None:
        """Replace the progress log on screen."""

        self._messages = list(messages)
        try:
            self.query_one("#progress-latest", Static).update(self._messages[-1])
            self.query_one("#progress-status", Static).update(
                _render_progress_log(self._messages)
            )
        except NoMatches:
            # The worker may publish progress before the progress screen finishes mounting.
            return


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
            with Vertical(classes="surface-frame"):
                with Vertical(classes="screen-header card card-shell"):
                    for widget in _header_widgets(
                        self._title,
                        "Review the final state, then restart if you want to run another install.",
                    ):
                        yield widget
                with Vertical(
                    classes="card card-error" if self._error else "card card-primary"
                ):
                    yield Static("Outcome", classes="card-title")
                    yield Static(self._summary, id=summary_id, classes="card-copy")
                with Horizontal(classes="button-row"):
                    yield Button("Start over", id="restart-button", variant="primary")
                yield Static(
                    _render_shortcut_bar(
                        ("Enter", "start over"),
                        ("R", "restart"),
                        ("Q", "quit"),
                    ),
                    classes="nav-strip",
                )

    def on_mount(self) -> None:
        """Focus the restart button to keep Enter useful on the result screen."""

        self.call_after_refresh(self._focus_restart_button)

    def _focus_restart_button(self) -> None:
        """Focus the restart button after layout."""

        self.query_one("#restart-button", Button).focus()

    def restart(self) -> None:
        """Reset the flow from the final screen."""

        _installer_app(self).show_query_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reset the flow from the final screen."""

        if event.button.id == "restart-button":
            self.restart()

    def on_key(self, event: events.Key) -> None:
        """Handle result-stage keyboard shortcuts."""

        if event.key == "r":
            self.restart()
            event.stop()
            event.prevent_default()
        elif event.key == "q":
            self.app.exit()
            event.stop()
            event.prevent_default()


class WorkflowServicePort(Protocol):
    """Protocol implemented by the shared install workflow service."""

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
        background: #101419;
        color: #e6edf3;
    }

    #surface {
        padding: 1 1;
    }

    .surface-frame {
        width: 1fr;
        max-width: 112;
        background: #0f1419;
        border: round #1f2a34;
        padding: 1 1;
    }

    .card-grid {
        height: auto;
    }

    .grid-card {
        width: 1fr;
    }

    .screen-header {
        background: #12181f;
        border: round #26323c;
    }

    .eyebrow {
        color: #8fa4b5;
        text-style: bold;
        margin-bottom: 0;
    }

    .page-title {
        color: #f1f5f9;
        text-style: bold;
        margin-bottom: 1;
    }

    .page-copy, .card-copy, .candidate-copy, .candidate-details, .status-note {
        color: #97a6b2;
    }

    .card {
        background: #151b22;
        border: round #2a3640;
        padding: 1 1;
        margin-bottom: 1;
    }

    .card-primary {
        border: round #3f5768;
        background: #18202a;
    }

    .card-secondary {
        border: round #2d3943;
    }

    .card-shell {
        padding-bottom: 0;
    }

    .card-error {
        border: round #6f4750;
        background: #21181a;
    }

    .card-title {
        color: #f1f5f9;
        text-style: bold;
        margin-bottom: 1;
    }

    .field-label {
        color: #8fa4b5;
        margin-top: 0;
        margin-bottom: 0;
    }

    Input, Select, Button {
        margin-bottom: 1;
    }

    Input, Select {
        background: #10161c;
        border: round #31404c;
        color: #e6edf3;
    }

    Button {
        background: #182029;
        border: round #33414c;
        color: #e6edf3;
        min-width: 20;
    }

    Button:focus {
        border: round #a3b7c8;
        background: #1d2730;
    }

    .button-row {
        height: auto;
        align-horizontal: right;
    }

    .meta-row {
        height: auto;
        margin-bottom: 1;
    }

    .meta-chip {
        width: auto;
        min-width: 12;
        padding: 0 1;
        margin-right: 1;
        background: #1b242d;
        border: round #32404b;
        color: #d2dbe3;
    }

    .meta-chip.accent {
        color: #d6e5f0;
        border: round #4a6273;
    }

    .meta-chip.muted {
        color: #b9c7d1;
        border: round #394651;
    }

    .candidate-card {
        padding-bottom: 1;
    }

    .candidate-card:focus-within {
        border: round #536877;
        background: #182028;
    }

    .candidate-title {
        color: #f1f5f9;
        text-style: bold;
    }

    .candidate-slug {
        color: #8fa4b5;
        margin-bottom: 1;
    }

    .candidate-reason {
        color: #e5ebf1;
        margin-bottom: 1;
    }

    #progress-status, #result-summary, #error-summary, #plan-overview, #plan-metadata, #plan-steps {
        background: #111820;
        border: round #31404c;
        padding: 1 2;
        height: auto;
    }

    #error-summary {
        border: round #7b5259;
        color: #f0d0d4;
    }

    .nav-strip {
        color: #7f909d;
        background: #12181f;
        border: round #28333d;
        padding: 0 1;
        margin-bottom: 0;
    }
    """

    BINDINGS = [
        *App.BINDINGS,
        Binding(
            "q",
            "quit",
            "Quit",
            show=False,
            priority=True,
            tooltip="Quit the app and return to the command prompt.",
        ),
    ]

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

    def action_back(self) -> None:
        """Trigger the available back action for the current screen."""

        if isinstance(self.screen, CandidateScreen):
            self.screen.go_back()
            return
        if isinstance(self.screen, PlanScreen):
            self.screen.go_back()

    def action_install_shortcut(self) -> None:
        """Start installation from the plan screen."""

        if isinstance(self.screen, PlanScreen):
            self.begin_install()

    def action_restart_shortcut(self) -> None:
        """Restart the flow from the result screen."""

        if isinstance(self.screen, ResultScreen):
            self.screen.restart()

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
            "Reviewing plan", "Resolving the query against the registry."
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
            "Applying the current profile and interaction settings.",
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
            self.append_progress,
            "Materializing the selected skill graph.",
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
