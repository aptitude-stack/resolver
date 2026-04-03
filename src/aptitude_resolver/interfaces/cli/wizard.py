"""Inline CLI wizard for guided Aptitude installs."""

from __future__ import annotations

import sys
import termios
import tty
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Generic,
    Literal,
    Mapping,
    Protocol,
    Sequence,
    TypeVar,
    cast,
)

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.text import Text

from aptitude_resolver.application.dto import (
    InstallResultDto,
    ResolveQueryResultDto,
    SyncResultDto,
)
from aptitude_resolver.application.composition import (
    build_install_use_case,
    build_resolve_use_case,
    build_sync_use_case,
)
from aptitude_resolver.domain.errors import (
    AptitudeResolverError,
    DiscoveryNoCandidatesError,
)
from aptitude_resolver.interfaces.cli.catalog import (
    THEME,
    render_wizard_manifest_panel,
)
from aptitude_resolver.interfaces.cli.support import (
    build_workflow_options,
    build_workflow_service as _shared_build_workflow_service,
    capture_cli_telemetry,
    format_cli_error,
    format_cli_install_telemetry_line,
    format_cli_telemetry_block,
    format_unexpected_cli_error,
)
from aptitude_resolver.interfaces.shared import (
    InstallWorkflowOptions,
    InstallWorkflowService,
    InteractionMode,
)


PROFILE_OPTIONS: list[tuple[str, str]] = [
    ("Balanced", "balanced"),
    ("Low cost", "low-cost"),
    ("High trust", "high-trust"),
]

WizardEntryFlow = Literal["install", "sync"]
WizardLauncherAction = Literal["install", "sync", "help", "exit"]
ReturnOption = Literal["__return__"]
DEFAULT_INSTALL_SELECTION_PROFILE = "balanced"
DEFAULT_INSTALL_INTERACTION_MODE: InteractionMode = "auto"

FLOW_OPTIONS: list[tuple[str, WizardLauncherAction]] = [
    ("Install from query", "install"),
    ("Sync from lockfile", "sync"),
    ("Help", "help"),
    ("Exit", "exit"),
]

FLOW_DESCRIPTIONS: dict[WizardLauncherAction, str] = {
    "install": "Guided fresh planning and materialization.",
    "sync": "Replay an existing lockfile into a local workspace.",
    "help": "Show the capability map and command guide.",
    "exit": "Leave the wizard without running a command.",
}

INTERACTION_OPTIONS: list[tuple[str, InteractionMode]] = [
    ("Auto", "auto"),
    ("Always ask", "always"),
    ("Never ask", "never"),
]

T = TypeVar("T")
BannerStyle = Literal["classic", "block"]
RETURN_OPTION_VALUE: ReturnOption = "__return__"
LARGE_TEXT_PROMPT_HEIGHT = 6
PLAN_SUMMARY_LABEL_WIDTH = len("Interaction")

WORDMARKS: dict[BannerStyle, str] = {
    "classic": (
        "\n"
        "   ______          __          \n"
        "  /\\  _  \\        /\\ \\__       \n"
        "  \\ \\ \\L\\ \\  _____\\ \\ ,_\\      \n"
        "   \\ \\  __ \\/\\ '__`\\ \\ \\/      \n"
        "    \\ \\ \\/\\ \\ \\ \\L\\ \\ \\ \\_  __ \n"
        "     \\ \\_\\ \\_\\ \\ ,__/\\ \\__\\/\\_\\\n"
        "      \\/_/\\/_/\\ \\ \\/  \\/__/\\/_/\n"
        "               \\ \\_\\           \n"
        "                \\/_/           \n\n"
    ),
    "block": (
        "     ░▒▓██████▓▒░░▒▓███████▓▒░▒▓████████▓▒░    \n"
        "    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░        \n"
        "    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░        \n"
        "    ░▒▓████████▓▒░▒▓███████▓▒░  ░▒▓█▓▒░        \n"
        "    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        ░▒▓█▓▒░        \n"
        "    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        ░▒▓█▓▒░▒▓██▓▒░ \n"
        "    ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        ░▒▓█▓▒░▒▓██▓▒░ \n"
        "                                                 \n"
        "                                                 \n"
    ),
}


class PromptText(Protocol):
    def __call__(
        self,
        label: str,
        default: str | None,
        *,
        large: bool = False,
    ) -> str: ...


class ConfirmPrompt(Protocol):
    def __call__(self, label: str, default: bool) -> bool: ...


class WizardCancelled(Exception):
    """Raised when the user cancels the wizard from an interactive prompt."""


class SelectPrompt(Protocol, Generic[T]):
    def __call__(
        self,
        title: str,
        options: Sequence[tuple[str, T]],
        help_text: str | None = None,
        descriptions: Mapping[T, str] | None = None,
    ) -> T: ...


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

    def sync_lock(
        self,
        *,
        lock_path: Path,
        target: Path,
    ) -> SyncResultDto: ...


def _build_workflow_service() -> InstallWorkflowService:
    """Create one workflow service using the current builder functions."""

    return _shared_build_workflow_service(
        resolve_builder=build_resolve_use_case,
        install_builder=build_install_use_case,
        sync_builder=build_sync_use_case,
    )


def _format_error(error: AptitudeResolverError) -> str:
    """Render one error payload for CLI output."""

    return format_cli_error(error)


def _render_wordmark(*, style: BannerStyle = "classic") -> str:
    """Render a filled Aptitude wordmark."""

    return WORDMARKS[style]


def _render_choice_line(
    label: str,
    *,
    active: bool,
    description: str | None = None,
) -> str:
    """Render one menu option with a minimal active marker."""

    marker = "●" if active else "○"
    if active and description:
        return f"{marker} {label} - {description}"
    return f"{marker} {label}"


def _with_return_option(
    options: Sequence[tuple[str, T]],
) -> list[tuple[str, T | ReturnOption]]:
    """Append one visible return action to a menu."""

    return [*options, ("Return", RETURN_OPTION_VALUE)]


def _render_cli_manifest() -> Panel:
    """Render a compact summary of public, advanced, and framework CLI surfaces."""

    return render_wizard_manifest_panel()


def _active_menu_description(
    options: Sequence[tuple[str, T]],
    *,
    index: int,
    descriptions: Mapping[T, str] | None,
) -> str | None:
    """Return the description for the currently active menu option."""

    if descriptions is None or not options:
        return None
    return descriptions.get(options[index][1])


def _format_plan_summary_row(*items: tuple[str, object]) -> str:
    """Render one aligned plan summary row."""

    return "\n".join(
        f"{label:<{PLAN_SUMMARY_LABEL_WIDTH}} : {value}" for label, value in items
    )


def _render_plan_panel(
    result: ResolveQueryResultDto,
    *,
    selection_profile: str,
    interaction_mode: InteractionMode,
    target: Path,
) -> Panel:
    """Render one compact plan review box."""

    selected = result.selected_coordinate
    assert selected is not None
    assert result.execution_plan is not None
    skill = result.selected_skill

    body = Group(
        Text(
            _format_plan_summary_row(
                ("Selected", f"{selected.slug}@{selected.version}"),
            ),
            style=THEME.text_primary,
        ),
        Text(
            _format_plan_summary_row(
                ("Runtime", skill.runtime if skill and skill.runtime else "unknown"),
            ),
            style=THEME.text_detail,
        ),
        Text(
            _format_plan_summary_row(
                ("Trust", skill.trust_tier if skill else "unknown"),
            ),
            style=THEME.text_detail,
        ),
        Text(
            _format_plan_summary_row(
                ("Lifecycle", skill.lifecycle_status if skill else "unknown"),
            ),
            style=THEME.text_detail,
        ),
        Text(
            _format_plan_summary_row(
                ("Profile", selection_profile),
            ),
            style=THEME.text_muted,
        ),
        Text(
            _format_plan_summary_row(
                ("Interaction", interaction_mode),
            ),
            style=THEME.text_muted,
        ),
        Text(
            _format_plan_summary_row(
                ("Target", target),
            ),
            style=THEME.text_muted,
        ),
        Text(""),
        Text("Execution Steps", style=THEME.text_primary),
        *[
            Text(
                f"{index}. {step.skill}@{step.version} → {step.action}",
                style=THEME.text_muted,
            )
            for index, step in enumerate(result.execution_plan.steps, start=1)
        ],
    )
    return Panel(
        body,
        title="Review Plan",
        border_style=THEME.border_secondary,
        box=box.ROUNDED,
        padding=(1, 1),
    )


def _render_materialization_panel(
    result: InstallResultDto | SyncResultDto,
    *,
    title: str = "Installed Skills",
    footer: str | None = None,
) -> Panel:
    """Render one compact materialization result box."""

    installed = (
        "\n".join(
            f"✓ {skill.slug}@{skill.version}\n  → {skill.install_path}"
            for skill in result.installed_skills
        )
        or "No skills materialized."
    )
    if footer:
        installed = f"{installed}\n\n{footer}"
    return Panel(
        Text(installed, style=THEME.text_body),
        title=title,
        border_style=THEME.border_secondary,
        box=box.ROUNDED,
        padding=(1, 1),
    )


def _render_step_separator(width: int) -> str:
    """Render the shared long separator used between wizard steps."""

    return "─" * max(1, width)


@contextmanager
def _use_rounded_prompt_border():
    """Temporarily switch prompt_toolkit frame corners to rounded glyphs."""

    widgets_base = sys.modules.get("prompt_toolkit.widgets.base")
    if widgets_base is None:
        import prompt_toolkit.widgets.base as widgets_base

    original_corners = (
        widgets_base.Border.TOP_LEFT,
        widgets_base.Border.TOP_RIGHT,
        widgets_base.Border.BOTTOM_LEFT,
        widgets_base.Border.BOTTOM_RIGHT,
    )
    widgets_base.Border.TOP_LEFT = "╭"
    widgets_base.Border.TOP_RIGHT = "╮"
    widgets_base.Border.BOTTOM_LEFT = "╰"
    widgets_base.Border.BOTTOM_RIGHT = "╯"
    try:
        yield
    finally:
        (
            widgets_base.Border.TOP_LEFT,
            widgets_base.Border.TOP_RIGHT,
            widgets_base.Border.BOTTOM_LEFT,
            widgets_base.Border.BOTTOM_RIGHT,
        ) = original_corners


def _default_prompt_text(
    label: str,
    default: str | None,
    *,
    large: bool = False,
) -> str:
    """Prompt for one text value using prompt_toolkit."""

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        suffix = f" [{default}]" if default else ""
        response = input(f"{label}{suffix}: ")
        return response or default or ""

    try:
        from prompt_toolkit import prompt
        from prompt_toolkit.application import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import HSplit, Window
        from prompt_toolkit.layout.dimension import Dimension
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.styles import Style
        from prompt_toolkit.widgets import Frame, TextArea
    except ModuleNotFoundError:
        suffix = f" [{default}]" if default else ""
        response = input(f"{label}{suffix}: ")
        return response or default or ""

    if large:
        text_area = TextArea(
            text=default or "",
            multiline=True,
            wrap_lines=True,
            scrollbar=False,
            style="class:body",
            focus_on_click=True,
            height=Dimension(
                preferred=LARGE_TEXT_PROMPT_HEIGHT,
                min=LARGE_TEXT_PROMPT_HEIGHT,
                max=LARGE_TEXT_PROMPT_HEIGHT,
            ),
        )
        bindings = KeyBindings()

        submit_hint = "[Shift+Enter] submit  [Ctrl+C] cancel"
        submit_candidates: list[tuple[tuple[str, ...], str]] = [
            (("s-enter",), "[Shift+Enter] submit  [Ctrl+C] cancel"),
            (("escape", "enter"), "[Esc, Enter] submit  [Ctrl+C] cancel"),
        ]
        if sys.platform == "darwin":
            # macOS terminals generally can't expose Command directly to prompt_toolkit.
            submit_candidates = [
                (("escape", "enter"), "[Cmd+Return] submit  [Ctrl+C] cancel"),
                (("s-enter",), "[Shift+Enter] submit  [Ctrl+C] cancel"),
            ]

        submit_binding = None
        for keys, hint in submit_candidates:
            try:
                submit_binding = bindings.add(*keys)
                submit_hint = hint
                break
            except ValueError:
                continue
        if submit_binding is None:
            raise ValueError("No valid key binding available for wizard submit.")

        @submit_binding
        def _accept(event) -> None:
            event.app.exit(result=text_area.text.strip())

        @bindings.add("c-c")
        def _abort(event) -> None:
            event.app.exit(exception=KeyboardInterrupt())

        header = Window(
            FormattedTextControl(
                [
                    ("class:title", f"{label}\n"),
                    (
                        "class:hint",
                        "Paste or type a longer search query.\n",
                    ),
                ]
            ),
            height=2,
            always_hide_cursor=True,
        )
        footer = Window(
            FormattedTextControl([("class:hint", submit_hint)]),
            height=1,
            always_hide_cursor=True,
        )
        with _use_rounded_prompt_border():
            prompt_frame = Frame(
                text_area,
                style="class:border",
            )
        prompt_stack = HSplit(
            [
                header,
                prompt_frame,
                footer,
            ],
        )
        application: Application[str] = Application(
            layout=Layout(
                prompt_stack,
                focused_element=text_area,
            ),
            key_bindings=bindings,
            mouse_support=False,
            full_screen=False,
            style=Style.from_dict(
                {
                    "title": "bold #ffffff",
                    "body": "#ffffff",
                    "hint": "#7a7a7a",
                    "border": "#4d4d4d",
                    "frame.border": "#4d4d4d",
                    "text-area": "#ffffff",
                }
            ),
        )
        return application.run() or default or ""

    prompt_label = f"{label}: "
    return prompt(prompt_label, default=default or "")


def _fallback_select_one(
    title: str,
    options: Sequence[tuple[str, T]],
    help_text: str | None = None,
    descriptions: Mapping[T, str] | None = None,
) -> T:
    """Select one option without prompt_toolkit."""

    if not options:
        raise ValueError("Expected at least one option.")

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(title)
        if help_text:
            print(help_text)
        for index, (label, _) in enumerate(options, start=1):
            print(f"  {index}. {label}")
        while True:
            raw_choice = input("Select option by number: ").strip()
            if raw_choice.lower() == "q":
                raise WizardCancelled()
            try:
                index = int(raw_choice)
            except ValueError:
                print("Enter a valid number.")
                continue
            if 1 <= index <= len(options):
                return options[index - 1][1]
            print("Selection out of range.")

    index = 0

    def render_lines() -> list[str]:
        lines = [title]
        if help_text:
            lines.append(help_text)
        lines.append("")
        for option_index, (label, _) in enumerate(options):
            lines.append(
                _render_choice_line(
                    label,
                    active=option_index == index,
                    description=_active_menu_description(
                        options,
                        index=index,
                        descriptions=descriptions,
                    )
                    if option_index == index
                    else None,
                )
            )
        lines.append("")
        lines.append("[↑↓] move  [enter] confirm  [q] cancel")
        lines.append("")
        return lines

    def draw(lines: list[str]) -> None:
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write("\n".join(lines))
        sys.stdout.flush()

    def read_key() -> str:
        first = sys.stdin.read(1)
        if first != "\x1b":
            return first
        second = sys.stdin.read(1)
        third = sys.stdin.read(1)
        return first + second + third

    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdout.write("\x1b[?25l")
        draw(render_lines())
        while True:
            key = read_key()
            if key == "\x1b[A":
                index = (index - 1) % len(options)
                draw(render_lines())
            elif key == "\x1b[B":
                index = (index + 1) % len(options)
                draw(render_lines())
            elif key in {"\r", "\n"}:
                sys.stdout.write("\x1b[2J\x1b[H\n\x1b[?25h")
                sys.stdout.flush()
                return options[index][1]
            elif key in {"q", "\x03"}:
                sys.stdout.write("\x1b[2J\x1b[H\n\x1b[?25h")
                sys.stdout.flush()
                raise WizardCancelled()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()


def _default_select_one(
    title: str,
    options: Sequence[tuple[str, T]],
    help_text: str | None = None,
    descriptions: Mapping[T, str] | None = None,
) -> T:
    """Select one option with an inline keyboard-driven menu."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return _fallback_select_one(title, options, help_text, descriptions)

    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import HSplit, Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.styles import Style
    except ModuleNotFoundError:
        return _fallback_select_one(title, options, help_text, descriptions)

    if not options:
        raise ValueError("Expected at least one option.")

    state = {"index": 0}

    def render_menu() -> list[tuple[str, str]]:
        fragments: list[tuple[str, str]] = [("class:title", f"{title}\n")]
        if help_text:
            fragments.append(("class:hint", f"{help_text}\n"))
        fragments.append(("class:hint", "\n"))
        active_description = _active_menu_description(
            options,
            index=state["index"],
            descriptions=descriptions,
        )
        for index, (label, _) in enumerate(options):
            is_active = index == state["index"]
            marker = "●" if is_active else "○"
            marker_style = "class:marker-active" if is_active else "class:item"
            label_style = "class:active" if is_active else "class:item"
            fragments.append((marker_style, f"{marker} "))
            fragments.append((label_style, label))
            if is_active and active_description:
                fragments.append(("class:detail", f" - {active_description}"))
            fragments.append(("", "\n"))
        fragments.append(("class:hint", "\n[↑↓] move  [enter] confirm  [q] cancel\n\n"))
        return fragments

    control = FormattedTextControl(render_menu, focusable=True)
    bindings = KeyBindings()

    @bindings.add("up")
    def _move_up(event) -> None:
        state["index"] = (state["index"] - 1) % len(options)
        event.app.invalidate()

    @bindings.add("down")
    def _move_down(event) -> None:
        state["index"] = (state["index"] + 1) % len(options)
        event.app.invalidate()

    @bindings.add("enter")
    def _accept(event) -> None:
        event.app.exit(result=options[state["index"]][1])

    @bindings.add("q")
    @bindings.add("c-c")
    def _abort(event) -> None:
        event.app.exit(exception=WizardCancelled())

    application: Application[T] = Application(
        layout=Layout(HSplit([Window(control, always_hide_cursor=True)])),
        key_bindings=bindings,
        mouse_support=False,
        full_screen=False,
        style=Style.from_dict(
            {
                "title": "bold #ffffff",
                "item": "#b8b8b8",
                "active": "bold #ffffff",
                "marker-active": f"bold {THEME.accent}",
                "hint": "#7a7a7a",
                "detail": "#d8d8d8",
            }
        ),
    )
    return application.run()


def _default_confirm(label: str, default: bool) -> bool:
    """Confirm one choice with the inline menu helper."""

    default_index = 0 if default else 1
    ordered = [("Yes", True), ("No", False)]
    if default_index == 1:
        ordered = [("No", False), ("Yes", True)]
    return _default_select_one(label, ordered)


class CliWizard:
    """Streamed CLI wizard for install flows."""

    def __init__(
        self,
        *,
        workflow_service: WorkflowServicePort | None = None,
        console: Console | None = None,
        prompt_text: PromptText | None = None,
        select_one: SelectPrompt[object] | None = None,
        confirm: ConfirmPrompt | None = None,
        target: Path = Path("skill_demo"),
        banner_style: BannerStyle = "classic",
    ) -> None:
        self._workflow_service = workflow_service or _build_workflow_service()
        self._console = console or Console()
        self._prompt_text = prompt_text or _default_prompt_text
        self._select_one = select_one or _default_select_one
        self._confirm = confirm or _default_confirm
        self._target = target
        self._banner_style = banner_style

    def _select(
        self,
        title: str,
        options: Sequence[tuple[str, T]],
        help_text: str | None = None,
        descriptions: Mapping[T, str] | None = None,
    ) -> T:
        """Return one typed selection from the generic menu helper."""

        object_descriptions = (
            cast(Mapping[object, str], descriptions)
            if descriptions is not None
            else None
        )
        return cast(
            T,
            self._select_one(
                title,
                cast(Sequence[tuple[str, object]], options),
                help_text,
                object_descriptions,
            ),
        )

    def run(
        self,
        initial_flow: WizardEntryFlow | None = None,
        *,
        initial_query: str | None = None,
    ) -> None:
        """Run the inline wizard launcher."""
        try:
            self._render_header(initial_flow=initial_flow)
            flow: WizardLauncherAction | None = initial_flow
            launcher_menu_rendered = False
            while True:
                if flow is None:
                    if launcher_menu_rendered:
                        self._print_step_separator()
                    selected_flow: WizardLauncherAction = self._select(
                        "Choose a flow",
                        FLOW_OPTIONS,
                        "Start with install, sync, or help.",
                        FLOW_DESCRIPTIONS,
                    )
                    launcher_menu_rendered = True
                    flow = selected_flow
                if flow == "help":
                    self._console.print(_render_cli_manifest())
                    flow = None
                    continue
                if flow == "exit":
                    self._console.print("Exited.", style="yellow")
                    return
                if flow == "sync":
                    sync_result = self._run_sync_flow()
                    self._print_step_separator()
                    self._console.print(_render_materialization_panel(sync_result))
                    return

                install_outcome = self._run_install_flow(
                    initial_query=initial_query,
                    direct_install_entry=initial_flow == "install",
                )
                if install_outcome is None:
                    return
                install_result, telemetry_summary = install_outcome
                self._print_step_separator()
                self._console.print(
                    _render_materialization_panel(
                        install_result,
                        title="Installation Summary",
                        footer=telemetry_summary,
                    )
                )
                return
        except (AptitudeResolverError,) as exc:
            self._console.print(_format_error(exc), style="red")
            return
        except (KeyboardInterrupt, EOFError, WizardCancelled):
            self._console.print("Cancelled.", style="yellow")
            return
        except Exception as exc:
            self._console.print(format_unexpected_cli_error(exc), style="red")
            return

    def _run_install_flow(
        self,
        *,
        initial_query: str | None = None,
        direct_install_entry: bool = False,
    ) -> tuple[InstallResultDto, str | None] | None:
        """Run the guided install flow after the user selects it."""

        query = initial_query.strip() if initial_query is not None else None
        skip_initial_separator = direct_install_entry and query is not None
        if query is None:
            self._print_step_separator()
            query = self._prompt_install_query()
        if not query:
            self._console.print("No query entered. Exiting.", style="yellow")
            return None

        while True:
            if skip_initial_separator:
                skip_initial_separator = False
            else:
                self._print_step_separator()
            selection_profile = self._select(
                "Selection profile",
                _with_return_option(PROFILE_OPTIONS),
                "Choose how candidates should be ranked.",
            )
            if selection_profile == RETURN_OPTION_VALUE:
                self._print_step_separator()
                query = self._prompt_install_query()
                if not query:
                    self._console.print("No query entered. Exiting.", style="yellow")
                    return None
                continue

            while True:
                retry_query = False
                self._print_step_separator()
                interaction_mode = self._select(
                    "Interaction mode",
                    _with_return_option(INTERACTION_OPTIONS),
                    "Choose how ambiguity should be handled.",
                )
                if interaction_mode == RETURN_OPTION_VALUE:
                    break

                options = build_workflow_options(
                    prefer=str(selection_profile),
                    interaction_mode=interaction_mode,
                )

                while True:
                    try:
                        resolve_result = self._resolve(query=query, options=options)
                    except DiscoveryNoCandidatesError as exc:
                        self._print_step_separator()
                        self._console.print(_format_error(exc), style="red")
                        self._print_step_separator()
                        query = self._prompt_install_query()
                        if not query:
                            self._console.print(
                                "No query entered. Exiting.",
                                style="yellow",
                            )
                            return None
                        retry_query = True
                        break

                    if resolve_result is None:
                        break

                    self._print_step_separator()
                    self._console.print(
                        _render_plan_panel(
                            resolve_result,
                            selection_profile=str(selection_profile),
                            interaction_mode=interaction_mode,
                            target=self._target,
                        )
                    )
                    self._print_step_separator()
                    if not self._confirm("Proceed with installation?", True):
                        self._console.print("Installation cancelled.", style="yellow")
                        return None

                    return self._install(
                        query=query,
                        select_slug=resolve_result.selected_coordinate.slug
                        if resolve_result.selected_coordinate is not None
                        else None,
                        options=options,
                    )

                if retry_query:
                    break
                if resolve_result is None:
                    continue

            if retry_query:
                continue

    def _prompt_install_query(self) -> str:
        """Prompt for one install query using the larger free-text surface."""

        return self._prompt_text("Install query", None, large=True).strip()

    def _print_operation_telemetry(
        self,
        operation_label: str,
        stage_timings,
        *,
        compact: bool = False,
    ) -> None:
        """Render one operation-scoped telemetry block inside the wizard flow."""

        summary = (
            format_cli_install_telemetry_line(stage_timings)
            if compact
            else format_cli_telemetry_block(operation_label, stage_timings)
        )
        if summary is None:
            return
        self._console.print(Text(summary, style=THEME.text_subtle), end="\n\n")

    def _run_sync_flow(self) -> SyncResultDto:
        """Run the guided sync flow after the user selects it."""

        self._print_step_separator()
        lock_path = Path(
            self._prompt_text("Lockfile path", "aptitude.lock.json").strip()
            or "aptitude.lock.json"
        )
        self._print_step_separator()
        target = Path(
            self._prompt_text("Target directory", str(self._target)).strip()
            or str(self._target)
        )

        telemetry = []
        try:
            with self._console.status(
                f"[{THEME.text_primary}]Syncing lockfile...", spinner="dots"
            ):
                with capture_cli_telemetry() as telemetry:
                    result = self._workflow_service.sync_lock(
                        lock_path=lock_path,
                        target=target,
                    )
        except Exception:
            self._print_operation_telemetry("Sync", telemetry)
            raise
        self._print_operation_telemetry("Sync", telemetry)
        return result

    def _resolve(
        self,
        *,
        query: str,
        options: InstallWorkflowOptions,
    ) -> ResolveQueryResultDto | None:
        """Resolve one query and select a candidate when needed."""

        telemetry = []
        try:
            with self._console.status(
                f"[{THEME.text_primary}]Resolving query...", spinner="dots"
            ):
                with capture_cli_telemetry() as telemetry:
                    result = self._workflow_service.resolve_query(
                        query=query,
                        version=None,
                        select_slug=None,
                        interaction_mode=None,
                        prompt_capable=False,
                        selection_source="wizard",
                        options=options,
                    )
        except Exception:
            self._print_operation_telemetry("Resolve query", telemetry)
            raise
        self._print_operation_telemetry("Resolve query", telemetry)

        if result.status != "selection_required":
            return result

        candidate_options = _with_return_option(
            [
                (
                    f"{candidate.slug}@{candidate.version}  {candidate.runtime or 'unknown'}  "
                    f"{candidate.trust_tier}  {candidate.lifecycle_status}",
                    candidate.slug,
                )
                for candidate in result.candidates
            ]
        )
        chosen_slug = self._select(
            "Select candidate",
            candidate_options,
            "Multiple matches found. Pick one candidate.",
        )
        if chosen_slug == RETURN_OPTION_VALUE:
            return None
        telemetry = []
        try:
            with self._console.status(
                f"[{THEME.text_primary}]Applying candidate...", spinner="dots"
            ):
                with capture_cli_telemetry() as telemetry:
                    result = self._workflow_service.resolve_query(
                        query=query,
                        version=None,
                        select_slug=str(chosen_slug),
                        interaction_mode="never",
                        prompt_capable=False,
                        selection_source="wizard",
                        options=options,
                    )
        except Exception:
            self._print_operation_telemetry("Apply candidate", telemetry)
            raise
        self._print_operation_telemetry("Apply candidate", telemetry)
        return result

    def _install(
        self,
        *,
        query: str,
        select_slug: str | None,
        options: InstallWorkflowOptions,
    ) -> tuple[InstallResultDto, str | None]:
        """Install one resolved selection."""

        telemetry = []
        try:
            with Progress(
                SpinnerColumn(style=THEME.accent),
                TextColumn(f"[{THEME.text_primary}]{{task.description}}"),
                BarColumn(
                    bar_width=28,
                    complete_style=THEME.accent,
                    finished_style=THEME.accent,
                ),
                transient=True,
                console=self._console,
            ) as progress:
                task = progress.add_task("Installing skill graph", total=100)
                progress.advance(task, 20)
                with capture_cli_telemetry() as telemetry:
                    result = self._workflow_service.install_query(
                        query=query,
                        version=None,
                        select_slug=select_slug,
                        target=self._target,
                        interaction_mode=None,
                        prompt_capable=False,
                        selection_source="wizard",
                        options=options,
                    )
                progress.advance(task, 80)
        except Exception:
            self._print_operation_telemetry("Install", telemetry, compact=True)
            raise
        return result, format_cli_install_telemetry_line(telemetry)

    def _render_header(self, *, initial_flow: WizardEntryFlow | None = None) -> None:
        """Print the wizard header."""

        self._console.print(
            Text(_render_wordmark(style=self._banner_style), style=THEME.text_primary)
        )
        self._console.print(
            Text.assemble(
                ("Aptitude", THEME.text_primary),
                (
                    " - Review-first CLI for discovering and installing skills.",
                    THEME.text_muted,
                ),
            )
        )
        self._write_separator()
        if initial_flow is None or initial_flow == "install":
            return

        self._console.print(Text(f"guided {initial_flow} flow", style=THEME.text_muted))

    def _print_step_separator(self) -> None:
        """Print one blank-line-separated divider between wizard steps."""

        self._write_separator(prefix_newline=True, suffix_newline=True)

    def _write_separator(
        self,
        *,
        prefix_newline: bool = False,
        suffix_newline: bool = False,
    ) -> None:
        """Write one exact separator line without Rich reflow."""

        prefix = "\n" if prefix_newline else ""
        suffix = "\n\n" if suffix_newline else "\n\n"
        self._console.file.write(
            f"{prefix}{_render_step_separator(self._console.size.width)}{suffix}"
        )
        flush = getattr(self._console.file, "flush", None)
        if callable(flush):
            flush()


def run_cli_wizard(
    *,
    initial_flow: WizardEntryFlow | None = None,
    initial_query: str | None = None,
    target: Path = Path("skill_demo"),
    banner_style: BannerStyle = "classic",
) -> None:
    """Launch the inline CLI wizard, optionally entering one flow directly."""

    CliWizard(target=target, banner_style=banner_style).run(
        initial_flow=initial_flow,
        initial_query=initial_query,
    )
