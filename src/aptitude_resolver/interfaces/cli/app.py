"""Typer application for the Aptitude CLI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys
from typing import TypeVar

import typer
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from aptitude_resolver.application.composition import (
    build_effective_policy_report,
    build_install_use_case,
    build_resolve_use_case,
    build_sync_use_case,
)
from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    EffectivePolicyReportDto,
    InstallResultDto,
    ResolveQueryResultDto,
    SyncResultDto,
)
from aptitude_resolver.domain.errors import (
    AptitudeResolverError,
    InvalidResolverConfigurationError,
)
from aptitude_resolver.interfaces.cli.catalog import (
    COMMANDS,
    HORIZONTAL_SEPARATOR,
    OPTIONS,
    THEME,
    build_command_help,
    build_manifest_text,
    build_root_help,
    resolve_cli_program_name,
)
from aptitude_resolver.interfaces.cli.wizard import (
    can_launch_cli_wizard,
    run_cli_wizard,
)
from aptitude_resolver.interfaces.cli.support import (
    build_workflow_options,
    build_workflow_service as _shared_build_workflow_service,
    can_prompt_user,
    capture_cli_telemetry,
    format_cli_error,
    format_cli_install_telemetry_line,
    format_cli_telemetry_block,
    format_unexpected_cli_error,
    has_interactive_output,
    parse_csv_option,
    parse_interaction_mode,
    parse_missing_environment_variables,
    resolve_cli_version,
)
from aptitude_resolver.interfaces.shared import (
    InteractionMode,
    InstallWorkflowOptions,
    InstallWorkflowService,
)

app = typer.Typer(
    no_args_is_help=True,
    help=build_root_help(),
    add_completion=False,
)
policy_app = typer.Typer(
    no_args_is_help=True,
    help=build_command_help("policy"),
    add_completion=False,
)
app.add_typer(policy_app, name="policy", help=build_command_help("policy"))
T = TypeVar("T")
_ACTIVITY_CONSOLE = Console(stderr=True)


def configure_help_surfaces(program_name: str | None = None) -> None:
    """Refresh root and subcommand help text for the active executable."""

    app.info.help = build_root_help(program_name)
    command_names_by_callback = {
        "resolve": "resolve",
        "install": "install",
        "sync": "sync",
        "demo": "demo",
        "manifest": "manifest",
        "show_policy": "policy_show",
    }
    for command_info in app.registered_commands:
        callback = command_info.callback
        if callback is None:
            continue
        callback_name = callback.__name__
        command_name = command_names_by_callback.get(callback_name)
        if command_name is None:
            continue
        command_info.help = build_command_help(command_name, program_name=program_name)
    policy_app.info.help = build_command_help("policy", program_name=program_name)
    for command_info in policy_app.registered_commands:
        callback = command_info.callback
        if callback is None:
            continue
        if callback.__name__ == "show_policy":
            command_info.help = build_command_help(
                "policy_show", program_name=program_name
            )


def _version_callback(value: bool) -> None:
    """Print the current Aptitude version and exit when requested."""

    if not value:
        return
    typer.echo(resolve_cli_version())
    raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help=OPTIONS["root_version"].help_text,
    ),
) -> None:
    """Aptitude CLI root command group."""


def _format_error(error: AptitudeResolverError) -> str:
    """Backwards-compatible wrapper for shared CLI error formatting."""

    return format_cli_error(error)


def _format_environment_configuration_error(
    error: InvalidResolverConfigurationError,
) -> str:
    """Backwards-compatible wrapper for shared environment error rendering."""

    return format_cli_error(error)


def _parse_missing_environment_variables(details: str) -> list[str]:
    """Backwards-compatible wrapper for shared parsing logic."""

    return parse_missing_environment_variables(details)


def _build_workflow_service() -> InstallWorkflowService:
    """Create one workflow service using the current builder functions."""

    return _shared_build_workflow_service(
        resolve_builder=build_resolve_use_case,
        install_builder=build_install_use_case,
        sync_builder=build_sync_use_case,
    )


def _parse_csv_option(
    value: str | None,
    *,
    option_name: str,
) -> list[str] | None:
    """Backwards-compatible wrapper for shared CSV parsing."""

    return parse_csv_option(value, option_name=option_name)


def _parse_interaction_mode(value: str | None) -> InteractionMode | None:
    """Backwards-compatible wrapper for shared interaction-mode parsing."""

    return parse_interaction_mode(value)


def _can_prompt_user() -> bool:
    """Backwards-compatible wrapper for prompt capability detection."""

    return can_prompt_user()


def _has_interactive_output() -> bool:
    """Backwards-compatible wrapper for rich output capability detection."""

    return has_interactive_output()


def _stdout_console() -> Console:
    """Return one stdout console bound to the current stream."""

    return Console(file=sys.stdout)


def _stderr_console() -> Console:
    """Return one stderr console bound to the current stream."""

    return Console(file=sys.stderr, stderr=True)


def _stream_supports_text(stream: object, text: str) -> bool:
    """Return whether the given stream encoding can represent the sample text."""

    encoding = getattr(stream, "encoding", None)
    if not encoding:
        return True

    try:
        text.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def _panel_box_for_stream(stream: object):
    """Return the best available Rich box style for the current stream."""

    if _stream_supports_text(stream, "╭╮╰╯│─"):
        return box.ROUNDED
    return box.ASCII


def _text_separator(stream: object) -> str:
    """Return a safe plain-text separator for the current stream."""

    if _stream_supports_text(stream, HORIZONTAL_SEPARATOR):
        return HORIZONTAL_SEPARATOR
    return "-" * 100


def _render_candidate(index: int, candidate: DiscoveryCandidateDto) -> str:
    """Render one candidate line for interactive selection."""

    labels = ", ".join(candidate.matched_labels or candidate.labels[:4])
    label_suffix = f" [{labels}]" if labels else ""
    lines = [
        f"{index}. {candidate.slug}@{candidate.version} - {candidate.name}"
        f" ({candidate.runtime or 'unknown runtime'}, {candidate.trust_tier}, {candidate.lifecycle_status})"
        f"{label_suffix}"
    ]
    if candidate.selection_details:
        lines.append(f"   {' | '.join(candidate.selection_details)}")
    if candidate.selection_reason:
        lines.append(f"   why ranked here: {candidate.selection_reason}")
    return "\n".join(lines)


def _run_with_activity(
    description: str,
    operation: Callable[[], T],
    *,
    show_bar: bool = False,
) -> T:
    """Run one CLI operation with transient progress in interactive sessions."""

    if not _has_interactive_output():
        return operation()

    if show_bar:
        with Progress(
            SpinnerColumn(style=THEME.accent),
            TextColumn(f"[{THEME.text_primary}]{{task.description}}"),
            BarColumn(
                bar_width=28,
                complete_style=THEME.accent,
                finished_style=THEME.accent,
            ),
            transient=True,
            console=_ACTIVITY_CONSOLE,
        ) as progress:
            task = progress.add_task(description, total=100)
            progress.advance(task, 20)
            result = operation()
            progress.advance(task, 80)
        return result

    with _ACTIVITY_CONSOLE.status(
        f"[{THEME.text_primary}]{description}",
        spinner="dots",
    ):
        return operation()


def _render_operation_telemetry(
    operation_label: str,
    stage_timings,
    *,
    compact: bool = False,
) -> None:
    """Render one operation-scoped telemetry block for interactive human CLI runs."""

    if not _has_interactive_output():
        return
    summary = (
        format_cli_install_telemetry_line(stage_timings)
        if compact
        else format_cli_telemetry_block(operation_label, stage_timings)
    )
    if summary is None:
        return
    _ACTIVITY_CONSOLE.print(summary, style=THEME.text_subtle)


def _prompt_for_candidate_slug(candidates: list[DiscoveryCandidateDto]) -> str:
    """Prompt the user to pick one candidate by index."""

    typer.echo("Multiple matching skills were found:")
    for index, candidate in enumerate(candidates, start=1):
        typer.echo(_render_candidate(index, candidate))

    while True:
        raw_choice = typer.prompt("Select a skill by number")
        try:
            selection = int(raw_choice)
        except ValueError:
            typer.echo("Please enter a valid candidate number.", err=True)
            continue

        if 1 <= selection <= len(candidates):
            return candidates[selection - 1].slug

        typer.echo("Selection is out of range. Try again.", err=True)


def _resolved_install_coordinates(result: InstallResultDto) -> list[tuple[str, str]]:
    """Return the installed coordinates in display order."""

    if result.installed_skills:
        return [(skill.slug, skill.version) for skill in result.installed_skills]

    if result.selected_coordinate is not None:
        return [(result.selected_coordinate.slug, result.selected_coordinate.version)]

    return []


def _format_install_success(
    result: InstallResultDto,
    *,
    telemetry_summary: str | None = None,
) -> str:
    """Render a human-friendly install summary inspired by package managers."""

    separator = _text_separator(sys.stdout)
    lines = [
        "Installation Summary",
        separator,
        f"Collecting {result.requested_query}",
    ]

    if result.selected_coordinate is not None:
        lines.append(
            "  Using resolver candidate "
            f"{result.selected_coordinate.slug} ({result.selected_coordinate.version})"
        )

    resolved_coordinates = _resolved_install_coordinates(result)
    selected_slug = (
        result.selected_coordinate.slug
        if result.selected_coordinate is not None
        else None
    )
    dependency_coordinates = [
        coordinate
        for coordinate in resolved_coordinates
        if coordinate[0] != selected_slug
    ]
    for dependency_slug, dependency_version in dependency_coordinates:
        lines.append(f"Collecting dependency {dependency_slug} ({dependency_version})")

    if resolved_coordinates:
        lines.append(separator)
        lines.append(
            "Installing collected resolver skills: "
            + ", ".join(slug for slug, _ in resolved_coordinates)
        )
        lines.append(
            "Successfully installed "
            + " ".join(f"{slug}-{version}" for slug, version in resolved_coordinates)
        )

    if result.materialized_root:
        lines.append(separator)
        lines.append(f"Installed to: {result.materialized_root}")

    if telemetry_summary:
        lines.append(separator)
        lines.append(telemetry_summary)

    return "\n".join(lines)


def _render_install_success_panel(
    result: InstallResultDto,
    *,
    telemetry_summary: str | None = None,
) -> Group:
    summary = Table.grid(expand=True, padding=(0, 2))
    summary.add_column(style=THEME.text_subtle, ratio=1)
    summary.add_column(style=THEME.text_primary, ratio=2)
    summary.add_row("Query", result.requested_query)
    if result.selected_coordinate is not None:
        summary.add_row(
            "Selected",
            f"{result.selected_coordinate.slug} ({result.selected_coordinate.version})",
        )
    if result.materialized_root:
        summary.add_row("Installed to", str(result.materialized_root))

    installed = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    installed.add_column("Skill", style=THEME.text_primary, min_width=18)
    installed.add_column("Version", style=THEME.text_subtle, min_width=10, no_wrap=True)
    installed.add_column("Path", style=THEME.text_body, ratio=3)
    for skill in result.installed_skills:
        installed.add_row(skill.slug, skill.version, skill.install_path)

    panels: list[Panel] = [
        Panel(
            summary,
            title="Installation Summary",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        )
    ]
    if result.installed_skills:
        panels.append(
            Panel(
                installed,
                title="Installed Skills",
                border_style=THEME.border_secondary,
                box=_panel_box_for_stream(sys.stdout),
                padding=(1, 1),
            )
        )
    if telemetry_summary is not None:
        panels.append(
            Panel(
                Text(telemetry_summary, style=THEME.text_body),
                title="Telemetry",
                border_style=THEME.border_secondary,
                box=_panel_box_for_stream(sys.stdout),
                padding=(1, 1),
            )
        )
    return Group(*panels)


def _format_sync_success(lock_path: Path, result: SyncResultDto) -> str:
    """Render a human-friendly sync summary inspired by package managers."""

    separator = _text_separator(sys.stdout)
    resolved_coordinates = [
        (skill.slug, skill.version) for skill in result.installed_skills
    ]
    lines = [
        "Sync summary",
        separator,
        f"Syncing locked resolver skills from {lock_path.resolve()}",
    ]
    if resolved_coordinates:
        lines.append(separator)
        lines.append(
            "Installing locked resolver skills: "
            + ", ".join(slug for slug, _ in resolved_coordinates)
        )
        lines.append(
            "Successfully synced "
            + " ".join(f"{slug}-{version}" for slug, version in resolved_coordinates)
        )
    if result.materialized_root:
        lines.append(separator)
        lines.append(f"Installed to: {result.materialized_root}")
    return "\n".join(lines)


def _render_sync_success_panel(lock_path: Path, result: SyncResultDto) -> Group:
    summary = Table.grid(expand=True, padding=(0, 2))
    summary.add_column(style=THEME.text_subtle, ratio=1)
    summary.add_column(style=THEME.text_primary, ratio=2)
    summary.add_row("Lockfile", str(lock_path.resolve()))
    if result.materialized_root:
        summary.add_row("Installed to", str(result.materialized_root))

    installed = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    installed.add_column("Skill", style=THEME.text_primary, min_width=18)
    installed.add_column("Version", style=THEME.text_subtle, min_width=10, no_wrap=True)
    installed.add_column("Path", style=THEME.text_body, ratio=3)
    for skill in result.installed_skills:
        installed.add_row(skill.slug, skill.version, skill.install_path)

    return Group(
        Panel(
            summary,
            title="Sync Summary",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
        Panel(
            installed,
            title="Installed Skills",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
    )


def _format_policy_list(values: list[str] | None) -> str:
    if not values:
        return "(none)"
    return ", ".join(values)


def _format_policy_limit(value: int | None) -> str:
    return "unlimited" if value is None else str(value)


def _source_label(source: str | None) -> str:
    mapping = {
        None: "Unknown",
        "default": "Default",
        "client_default": "Client default",
        "system_config": "System config",
        "user_config": "User config",
        "workspace_config": "Workspace config",
        "environment": "Environment",
        "cli_override": "CLI override",
    }
    return mapping.get(source, str(source).replace("_", " ").title())


def _render_layer_details(layer) -> list[str]:
    lines: list[str] = []
    selection = layer.selection
    if selection is not None:
        if selection.profile is not None:
            lines.append(f"profile {selection.profile}")
        if selection.interaction_mode is not None:
            lines.append(f"interaction {selection.interaction_mode}")

    policy = layer.policy
    if policy is not None:
        if policy.allowed_trust_tiers is not None:
            lines.append("trust " + _format_policy_list(policy.allowed_trust_tiers))
        if policy.allowed_lifecycle_statuses is not None:
            lines.append(
                "lifecycle " + _format_policy_list(policy.allowed_lifecycle_statuses)
            )
        if policy.max_token_estimate is not None:
            lines.append(f"skill tokens <= {policy.max_token_estimate}")
        if policy.max_content_size_bytes is not None:
            lines.append(f"skill bytes <= {policy.max_content_size_bytes}")
        if policy.max_total_token_estimate is not None:
            lines.append(f"graph tokens <= {policy.max_total_token_estimate}")
        if policy.max_total_content_size_bytes is not None:
            lines.append(f"graph bytes <= {policy.max_total_content_size_bytes}")

    return lines


def _policy_layer_status(report: EffectivePolicyReportDto, layer) -> tuple[str, str]:
    if layer.source == "default":
        return "Active", "Built-in defaults"
    if layer.source == "workspace_config" and layer.path is None:
        return "Not found", f"No aptitude.toml found upward from {report.cwd}"
    if layer.path is not None and not layer.active:
        return "Not found", layer.path
    if layer.path is not None and layer.active:
        details = _render_layer_details(layer)
        suffix = f" | {', '.join(details)}" if details else ""
        return "Loaded", f"{layer.path}{suffix}"
    if layer.active:
        details = _render_layer_details(layer)
        return "Active", ", ".join(details) if details else "Overrides applied"
    return "None", "No overrides"


def _format_policy_layer(line_report: EffectivePolicyReportDto, layer) -> list[str]:
    lines: list[str] = []
    if layer.source == "default":
        lines.append("default: built-in defaults")
    elif layer.source == "workspace_config" and layer.path is None:
        lines.append(
            f"workspace config: no aptitude.toml found upward from {line_report.cwd}"
        )
    elif layer.path is not None and layer.active:
        lines.append(f"{layer.label}: {layer.path}")
    elif layer.path is not None:
        lines.append(f"{layer.label}: {layer.path} (not present)")
    elif layer.active:
        lines.append(f"{layer.label}: active")
    else:
        lines.append(f"{layer.label}: no overrides")

    if layer.active:
        for detail in _render_layer_details(layer):
            lines.append(f"  {detail}")

    return lines


def _format_policy_report(report: EffectivePolicyReportDto) -> str:
    separator = _text_separator(sys.stdout)
    lines = [
        "Effective Selection",
        separator,
        (
            f"profile: {report.effective_selection.profile} "
            f"(from: {_source_label(report.effective_selection.profile_source)})"
        ),
        (
            f"interaction mode: {report.effective_selection.interaction_mode} "
            f"(from: {_source_label(report.effective_selection.interaction_mode_source)})"
        ),
        "",
        "Effective Policy",
        separator,
        f"from: {_source_label(report.effective_policy.source)}",
        (
            "allowed trust tiers: "
            + _format_policy_list(report.effective_policy.allowed_trust_tiers)
        ),
        (
            "allowed lifecycle statuses: "
            + _format_policy_list(report.effective_policy.allowed_lifecycle_statuses)
        ),
        (
            "per-skill token limit: "
            + _format_policy_limit(report.effective_policy.max_token_estimate)
        ),
        (
            "per-skill content size limit: "
            + _format_policy_limit(report.effective_policy.max_content_size_bytes)
        ),
        (
            "full-graph token limit: "
            + _format_policy_limit(report.effective_policy.max_total_token_estimate)
        ),
        (
            "full-graph content size limit: "
            + _format_policy_limit(report.effective_policy.max_total_content_size_bytes)
        ),
        "",
        "Config Sources",
        separator,
    ]
    for layer in report.layers:
        status, details = _policy_layer_status(report, layer)
        lines.append(f"{_source_label(layer.source)}: {status}")
        lines.append(f"  {details}")

    lines.extend(
        [
            "",
            "How It Works",
            separator,
            "selection: more specific values win",
            "  default -> system -> user -> workspace -> environment -> CLI",
            "policy: stricter values win",
            "  default -> system -> user -> workspace -> CLI",
            "install/resolve flags like --allow-trust are one-off policy overrides",
            "policy show shows the current effective baseline for this shell and these files",
        ]
    )
    return "\n".join(lines)


def _policy_summary_grid(report: EffectivePolicyReportDto) -> Table:
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(style=THEME.text_subtle, ratio=1)
    grid.add_column(style=THEME.text_primary, ratio=2)
    grid.add_row("Profile", str(report.effective_selection.profile))
    grid.add_row(
        "From",
        _source_label(report.effective_selection.profile_source),
    )
    grid.add_row("Interaction", str(report.effective_selection.interaction_mode))
    grid.add_row(
        "From",
        _source_label(report.effective_selection.interaction_mode_source),
    )
    return grid


def _policy_limits_grid(report: EffectivePolicyReportDto) -> Table:
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(style=THEME.text_subtle, ratio=1)
    grid.add_column(style=THEME.text_primary, ratio=2)
    grid.add_row("From", _source_label(report.effective_policy.source))
    grid.add_row(
        "Trust tiers",
        _format_policy_list(report.effective_policy.allowed_trust_tiers),
    )
    grid.add_row(
        "Lifecycle",
        _format_policy_list(report.effective_policy.allowed_lifecycle_statuses),
    )
    grid.add_row(
        "Skill token limit",
        _format_policy_limit(report.effective_policy.max_token_estimate),
    )
    grid.add_row(
        "Skill size limit",
        _format_policy_limit(report.effective_policy.max_content_size_bytes),
    )
    grid.add_row(
        "Graph token limit",
        _format_policy_limit(report.effective_policy.max_total_token_estimate),
    )
    grid.add_row(
        "Graph size limit",
        _format_policy_limit(report.effective_policy.max_total_content_size_bytes),
    )
    return grid


def _policy_sources_table(report: EffectivePolicyReportDto) -> Table:
    table = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    table.add_column("Source", style=THEME.text_primary, min_width=14, no_wrap=True)
    table.add_column("Status", style=THEME.text_subtle, min_width=10, no_wrap=True)
    table.add_column("Details", style=THEME.text_body, ratio=4)
    for layer in report.layers:
        status, details = _policy_layer_status(report, layer)
        table.add_row(_source_label(layer.source), status, details)
    return table


def _policy_explainer_text() -> Text:
    body = "\n".join(
        [
            "Selection: more specific values win.",
            "default -> system -> user -> workspace -> environment -> CLI",
            "",
            "Policy: stricter values win.",
            "default -> system -> user -> workspace -> CLI",
            "",
            "Install/resolve flags like --allow-trust are one-off policy overrides.",
            "policy show displays the current effective baseline for this shell and these files.",
        ]
    )
    return Text(body, style=THEME.text_body)


def _render_policy_report_panel(report: EffectivePolicyReportDto) -> Group:
    panel_box = _panel_box_for_stream(sys.stdout)
    return Group(
        Panel(
            _policy_summary_grid(report),
            title="Effective Selection",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        ),
        Panel(
            _policy_limits_grid(report),
            title="Effective Policy",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        ),
        Panel(
            _policy_sources_table(report),
            title="Config Sources",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        ),
        Panel(
            _policy_explainer_text(),
            title="How It Works",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        ),
    )


def _manifest_option_keys(command_name: str) -> tuple[str, ...]:
    if command_name == "install":
        return (
            "version_select",
            "select_slug",
            "prefer",
            "interaction_mode",
            "allow_trust",
            "allow_lifecycle",
            "max_tokens",
            "max_content_size",
            "install_target",
            "install_json",
        )
    if command_name == "sync":
        return ("lock", "sync_target", "sync_json")
    if command_name == "policy":
        return ("policy_json",)
    if command_name == "resolve":
        return (
            "version_select",
            "select_slug",
            "prefer",
            "interaction_mode",
            "allow_trust",
            "allow_lifecycle",
            "max_tokens",
            "max_content_size",
        )
    return ()


def _render_manifest_commands_table(command_names: list[str]) -> Table:
    table = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    table.add_column("Command", style=THEME.text_primary, min_width=12, no_wrap=True)
    table.add_column("Usage", style=THEME.text_body, ratio=2)
    table.add_column("Purpose", style=THEME.text_subtle, ratio=2)
    table.add_column("Flags", style=THEME.text_body, ratio=3)
    for command_name in command_names:
        command = COMMANDS[command_name]
        flags = ", ".join(
            OPTIONS[key].signature for key in _manifest_option_keys(command_name)
        )
        table.add_row(
            command.name,
            command.usage.format(cli="aptitude"),
            command.summary,
            flags or "-",
        )
    return table


def _render_manifest_flags_table() -> Table:
    table = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    table.add_column("Flag", style=THEME.text_primary, min_width=24, no_wrap=True)
    table.add_column("Purpose", style=THEME.text_body, ratio=3)
    for key in ("root_version", "help"):
        option = OPTIONS[key]
        table.add_row(option.signature, option.brief)
    return table


def _render_manifest_panel() -> Group:
    return Group(
        Panel(
            _render_manifest_commands_table(
                ["install", "sync", "policy", "demo", "manifest"]
            ),
            title="Public Commands",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
        Panel(
            _render_manifest_commands_table(["resolve"]),
            title="Advanced/Internal Commands",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
        Panel(
            _render_manifest_flags_table(),
            title="Global Flags",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
    )


def _demo_program_name() -> str:
    """Return the command name shown in demo walkthrough examples."""

    return resolve_cli_program_name()


def _demo_walkthrough_rows() -> list[tuple[str, str, str]]:
    """Return the recommended live demo order."""

    cli = _demo_program_name()
    return [
        (
            "1",
            cli,
            "Open the wizard-first entrypoint and show install, sync, help, and exit.",
        ),
        (
            "2",
            f'{cli} install "Postman Primary Skill"',
            "Show the happy path from query to planning, review, and materialization.",
        ),
        (
            "3",
            f'{cli} install "Postman" --interaction-mode always',
            "Show root ambiguity handling when several legal candidates match.",
        ),
        (
            "4",
            f"{cli} policy show",
            "Show the effective baseline: defaults plus system, user, workspace, environment, and CLI layers.",
        ),
        (
            "5",
            f"{cli} manifest",
            "Show the full supported CLI surface in one place.",
        ),
        (
            "6",
            f"{cli} sync --lock aptitude.lock.json",
            "Show lock replay without re-running live planning.",
        ),
    ]


def _demo_profile_rows() -> list[tuple[str, str, str]]:
    """Return the selection-profile explanations for the demo surface."""

    return [
        (
            "balanced",
            "Default profile. Tries to keep the overall choice practical and well-rounded.",
            "General product demos and ordinary installs.",
        ),
        (
            "low-cost",
            "Prefers lighter candidates when several legal options are otherwise similar.",
            "When the team wants smaller and cheaper skills where possible.",
        ),
        (
            "high-trust",
            "Prefers stronger trust signals when several legal options are otherwise similar.",
            "When governance or confidence matters more than minimal size.",
        ),
    ]


def _demo_interaction_rows() -> list[tuple[str, str]]:
    """Return the ambiguity-handling explanations for the demo surface."""

    return [
        ("auto", "Prompt only when ambiguity remains and the terminal can interact."),
        ("always", "Require an explicit user choice when ambiguity exists."),
        (
            "never",
            "Pick the top-ranked legal candidate deterministically without prompting.",
        ),
    ]


def _demo_policy_rows() -> list[tuple[str, str]]:
    """Return the plain-language policy explanations for the demo surface."""

    return [
        (
            "Selection preference",
            "Ranks legal candidates. Example: balanced, low-cost, or high-trust.",
        ),
        (
            "Policy",
            "Hard rules that decide what is allowed at all. Policy is about governance, not taste.",
        ),
        (
            "--allow-trust",
            "Allow only specific trust tiers such as verified or internal.",
        ),
        (
            "--allow-lifecycle",
            "Allow only specific lifecycle states such as published.",
        ),
        (
            "--max-tokens",
            "Reject skills or resolved graphs whose estimated token usage is above the configured ceiling.",
        ),
        (
            "--max-content-size",
            "Reject skills or resolved graphs whose content size is above the configured byte ceiling.",
        ),
        (
            "policy show",
            "Explains the current effective baseline and where it came from.",
        ),
    ]


def _demo_wizard_steps() -> list[str]:
    """Return the wizard steps shown in the demo surface."""

    return [
        "No arguments opens the wizard.",
        "Install flow: query -> profile -> interaction mode -> review plan -> install.",
        "Sync flow: lockfile path -> target directory -> materialize from lock.",
        "Help flow: compact capability map without leaving the wizard.",
    ]


def _build_demo_intro_panel() -> Panel:
    body = Group(
        Text(
            "Use this surface to frame the product before a live walkthrough.",
            style=THEME.text_body,
        ),
        Text(
            "Aptitude is a wizard-first CLI for fresh planning, policy inspection, lock replay, and capability discovery.",
            style=THEME.text_body,
        ),
        Text(
            f"Recommended order: run {_demo_program_name()} demo first, then follow the live commands below.",
            style=THEME.text_muted,
        ),
    )
    return Panel(
        body,
        title="CLI Demo Tour",
        border_style=THEME.border_secondary,
        box=_panel_box_for_stream(sys.stdout),
        padding=(1, 1),
    )


def _build_demo_walkthrough_table() -> Table:
    table = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    table.add_column("Step", style=THEME.text_primary, width=6, no_wrap=True)
    table.add_column("Command", style=THEME.text_primary, ratio=2)
    table.add_column("What To Highlight", style=THEME.text_body, ratio=3)
    for step, command, highlight in _demo_walkthrough_rows():
        table.add_row(step, command, highlight)
    return table


def _build_demo_profiles_table() -> Table:
    table = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    table.add_column("Profile", style=THEME.text_primary, min_width=12, no_wrap=True)
    table.add_column("Meaning", style=THEME.text_body, ratio=3)
    table.add_column("Typical Use", style=THEME.text_body, ratio=2)
    for profile, meaning, typical_use in _demo_profile_rows():
        table.add_row(profile, meaning, typical_use)
    return table


def _build_demo_interaction_table() -> Table:
    table = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    table.add_column("Mode", style=THEME.text_primary, min_width=10, no_wrap=True)
    table.add_column("Meaning", style=THEME.text_body, ratio=4)
    for mode, meaning in _demo_interaction_rows():
        table.add_row(mode, meaning)
    return table


def _build_demo_policy_table() -> Table:
    table = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    table.add_column("Concept", style=THEME.text_primary, min_width=18, no_wrap=True)
    table.add_column("Meaning", style=THEME.text_body, ratio=4)
    for concept, meaning in _demo_policy_rows():
        table.add_row(concept, meaning)
    return table


def _build_demo_wizard_panel() -> Panel:
    body = Group(
        *[
            Text(f"{index}. {step}", style=THEME.text_body)
            for index, step in enumerate(_demo_wizard_steps(), start=1)
        ]
    )
    return Panel(
        body,
        title="Wizard Walkthrough",
        border_style=THEME.border_secondary,
        box=_panel_box_for_stream(sys.stdout),
        padding=(1, 1),
    )


def _render_demo_panel() -> Group:
    return Group(
        _build_demo_intro_panel(),
        Panel(
            _build_demo_walkthrough_table(),
            title="Recommended Live Walkthrough",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
        Panel(
            _build_demo_profiles_table(),
            title="Selection Profiles",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
        Panel(
            _build_demo_interaction_table(),
            title="Interaction Modes",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
        Panel(
            _build_demo_policy_table(),
            title="Policy In Plain English",
            border_style=THEME.border_secondary,
            box=_panel_box_for_stream(sys.stdout),
            padding=(1, 1),
        ),
        _build_demo_wizard_panel(),
    )


def _format_demo_text() -> str:
    separator = _text_separator(sys.stdout)
    lines = [
        "Aptitude CLI demo tour",
        separator,
        "Use this command before a live walkthrough.",
        "Aptitude is a wizard-first CLI for fresh planning, policy inspection, lock replay, and capability discovery.",
        "",
        "Recommended live walkthrough",
        separator,
    ]
    for step, command, highlight in _demo_walkthrough_rows():
        lines.extend([f"{step}. {command}", f"   {highlight}"])

    lines.extend(["", "Selection profiles", separator])
    for profile, meaning, typical_use in _demo_profile_rows():
        lines.extend([f"- {profile}: {meaning}", f"  Best for: {typical_use}"])

    lines.extend(["", "Interaction modes", separator])
    for mode, meaning in _demo_interaction_rows():
        lines.append(f"- {mode}: {meaning}")

    lines.extend(["", "Policy in plain English", separator])
    for concept, meaning in _demo_policy_rows():
        lines.append(f"- {concept}: {meaning}")

    lines.extend(["", "Wizard walkthrough", separator])
    for index, step in enumerate(_demo_wizard_steps(), start=1):
        lines.append(f"{index}. {step}")

    return "\n".join(lines)


def _render_error_panel(message: str) -> Panel:
    lines = [
        line
        for line in message.splitlines()
        if line.strip() and line.strip() != HORIZONTAL_SEPARATOR
    ]
    title = (lines[0] if lines else "Aptitude error").rstrip(".")
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else message
    return Panel(
        Text(body, style=THEME.text_body),
        title=title,
        border_style=THEME.border_secondary,
        box=_panel_box_for_stream(sys.stderr),
        padding=(1, 1),
    )


def _emit_error_message(message: str) -> None:
    if _has_interactive_output():
        _stderr_console().print(_render_error_panel(message))
        return
    typer.echo(message, err=True)


def _emit_error(error: AptitudeResolverError) -> None:
    _emit_error_message(_format_error(error))


def _emit_unexpected_error(error: Exception) -> None:
    _emit_error_message(format_unexpected_cli_error(error))


def _resolve_query_result(
    workflow_service: InstallWorkflowService,
    *,
    query: str,
    version: str | None,
    select_slug: str | None,
    options: InstallWorkflowOptions,
) -> ResolveQueryResultDto:
    """Execute resolve and, if needed, complete interactive candidate selection."""

    prompt_capable = _can_prompt_user()
    use_case, close = workflow_service.prepare_resolve(options=options)
    try:
        with capture_cli_telemetry():
            result = workflow_service.execute_resolve(
                use_case,
                query=query,
                version=version,
                select_slug=select_slug,
                interaction_mode=None,
                prompt_capable=prompt_capable,
                selection_source=None,
            )
        if result.status != "selection_required":
            return result

        chosen_slug = _prompt_for_candidate_slug(result.candidates)
        with capture_cli_telemetry():
            return workflow_service.execute_resolve(
                use_case,
                query=query,
                version=version,
                select_slug=chosen_slug,
                interaction_mode="never",
                prompt_capable=False,
                selection_source="interactive",
            )
    finally:
        close()


def _install_result(
    workflow_service: InstallWorkflowService,
    *,
    query: str,
    version: str | None,
    select_slug: str | None,
    target: Path,
    options: InstallWorkflowOptions,
) -> InstallResultDto:
    """Execute install and, if needed, complete interactive candidate selection."""

    prompt_capable = _can_prompt_user()
    use_case, close = workflow_service.prepare_install(options=options)
    try:
        result = workflow_service.execute_install(
            use_case,
            query=query,
            version=version,
            select_slug=select_slug,
            target=target,
            interaction_mode=None,
            prompt_capable=prompt_capable,
            selection_source=None,
        )
        if result.status != "selection_required":
            return result

        chosen_slug = _prompt_for_candidate_slug(result.candidates)
        return workflow_service.execute_install(
            use_case,
            query=query,
            version=version,
            select_slug=chosen_slug,
            target=target,
            interaction_mode="never",
            prompt_capable=False,
            selection_source="interactive",
        )
    finally:
        close()


def _sync_result(
    workflow_service: InstallWorkflowService,
    *,
    lock_path: Path,
    target: Path,
) -> SyncResultDto:
    """Execute sync from one existing lockfile."""

    return workflow_service.sync_lock(lock_path=lock_path, target=target)


def _exit_for_missing_query() -> None:
    """Exit with a Typer-compatible missing-query error."""

    typer.echo("Missing argument 'QUERY'.", err=True)
    raise typer.Exit(code=2)


def _exit_for_missing_lock_option() -> None:
    """Exit with a Typer-compatible missing-lock error."""

    typer.echo("Missing option '--lock'.", err=True)
    raise typer.Exit(code=2)


def _can_launch_install_flow(
    *,
    query: str | None,
    version: str | None,
    select_slug: str | None,
    prefer: str | None,
    interaction_mode: str | None,
    allow_trust: str | None,
    allow_lifecycle: str | None,
    max_tokens: int | None,
    max_content_size: int | None,
    json_output: bool,
) -> bool:
    """Return whether a bare install invocation should open the guided flow."""

    return (
        version is None
        and select_slug is None
        and prefer is None
        and interaction_mode is None
        and allow_trust is None
        and allow_lifecycle is None
        and max_tokens is None
        and max_content_size is None
        and not json_output
    )


def _can_launch_sync_flow(
    *,
    lock_path: Path | None,
    json_output: bool,
) -> bool:
    """Return whether a bare sync invocation should open the guided flow."""

    return lock_path is None and not json_output


@app.command(hidden=True, help=build_command_help("resolve"))
def resolve(
    query: str,
    version: str | None = typer.Option(
        None,
        "--version",
        help=OPTIONS["version_select"].help_text,
    ),
    select_slug: str | None = typer.Option(
        None,
        "--select-slug",
        help=OPTIONS["select_slug"].help_text,
    ),
    prefer: str | None = typer.Option(
        None,
        "--prefer",
        help=OPTIONS["prefer"].help_text,
    ),
    interaction_mode: str | None = typer.Option(
        None,
        "--interaction-mode",
        help=OPTIONS["interaction_mode"].help_text,
    ),
    allow_trust: str | None = typer.Option(
        None,
        "--allow-trust",
        help=OPTIONS["allow_trust"].help_text,
    ),
    allow_lifecycle: str | None = typer.Option(
        None,
        "--allow-lifecycle",
        help=OPTIONS["allow_lifecycle"].help_text,
    ),
    max_tokens: int | None = typer.Option(
        None,
        "--max-tokens",
        min=0,
        help=OPTIONS["max_tokens"].help_text,
    ),
    max_content_size: int | None = typer.Option(
        None,
        "--max-content-size",
        min=0,
        help=OPTIONS["max_content_size"].help_text,
    ),
) -> None:
    """Resolve a skill query and print a stable JSON result."""

    options = build_workflow_options(
        prefer=prefer,
        interaction_mode=interaction_mode,
        allow_trust=allow_trust,
        allow_lifecycle=allow_lifecycle,
        max_tokens=max_tokens,
        max_content_size=max_content_size,
    )

    try:
        workflow_service = _build_workflow_service()
        result = _resolve_query_result(
            workflow_service,
            query=query,
            version=version,
            select_slug=select_slug,
            options=options,
        )
    except AptitudeResolverError as exc:
        _emit_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _emit_unexpected_error(exc)
        raise typer.Exit(code=1) from exc

    typer.echo(result.model_dump_json(indent=2, exclude_none=True))


@app.command(help=build_command_help("install"))
def install(
    query: str | None = typer.Argument(None),
    version: str | None = typer.Option(
        None,
        "--version",
        help=OPTIONS["version_select"].help_text,
    ),
    select_slug: str | None = typer.Option(
        None,
        "--select-slug",
        help=OPTIONS["select_slug"].help_text,
    ),
    prefer: str | None = typer.Option(
        None,
        "--prefer",
        help=OPTIONS["prefer"].help_text,
    ),
    interaction_mode: str | None = typer.Option(
        None,
        "--interaction-mode",
        help=OPTIONS["interaction_mode"].help_text,
    ),
    allow_trust: str | None = typer.Option(
        None,
        "--allow-trust",
        help=OPTIONS["allow_trust"].help_text,
    ),
    allow_lifecycle: str | None = typer.Option(
        None,
        "--allow-lifecycle",
        help=OPTIONS["allow_lifecycle"].help_text,
    ),
    max_tokens: int | None = typer.Option(
        None,
        "--max-tokens",
        min=0,
        help=OPTIONS["max_tokens"].help_text,
    ),
    max_content_size: int | None = typer.Option(
        None,
        "--max-content-size",
        min=0,
        help=OPTIONS["max_content_size"].help_text,
    ),
    target: Path = typer.Option(
        Path("skill_demo"),
        "--target",
        help=OPTIONS["install_target"].help_text,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=OPTIONS["install_json"].help_text,
    ),
) -> None:
    """Install a skill query into a local demo workspace."""

    if _can_launch_install_flow(
        query=query,
        version=version,
        select_slug=select_slug,
        prefer=prefer,
        interaction_mode=interaction_mode,
        allow_trust=allow_trust,
        allow_lifecycle=allow_lifecycle,
        max_tokens=max_tokens,
        max_content_size=max_content_size,
        json_output=json_output,
    ):
        if can_launch_cli_wizard():
            if query is None:
                run_cli_wizard(initial_flow="install", target=target)
            else:
                run_cli_wizard(
                    initial_flow="install",
                    initial_query=query,
                    target=target,
                )
            return

    if query is None:
        _exit_for_missing_query()
        raise AssertionError("unreachable")
    install_query = query

    options = build_workflow_options(
        prefer=prefer,
        interaction_mode=interaction_mode,
        allow_trust=allow_trust,
        allow_lifecycle=allow_lifecycle,
        max_tokens=max_tokens,
        max_content_size=max_content_size,
    )

    try:
        workflow_service = _build_workflow_service()
        with capture_cli_telemetry() as telemetry:
            result = _run_with_activity(
                "Planning and installing resolver skills",
                lambda: _install_result(
                    workflow_service,
                    query=install_query,
                    version=version,
                    select_slug=select_slug,
                    target=target,
                    options=options,
                ),
                show_bar=not json_output,
            )
    except AptitudeResolverError as exc:
        _emit_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _emit_unexpected_error(exc)
        raise typer.Exit(code=1) from exc

    if json_output or result.status != "installed":
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    if _has_interactive_output():
        _stdout_console().print(
            _render_install_success_panel(
                result,
                telemetry_summary=format_cli_install_telemetry_line(telemetry),
            )
        )
        return

    typer.echo(
        _format_install_success(
            result,
            telemetry_summary=format_cli_install_telemetry_line(telemetry),
        )
    )


@app.command(help=build_command_help("sync"))
def sync(
    lock_path: Path | None = typer.Option(
        None,
        "--lock",
        help=OPTIONS["lock"].help_text,
    ),
    target: Path = typer.Option(
        Path("skill_demo"),
        "--target",
        help=OPTIONS["sync_target"].help_text,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=OPTIONS["sync_json"].help_text,
    ),
) -> None:
    """Materialize a locked system from an existing lockfile."""

    if _can_launch_sync_flow(lock_path=lock_path, json_output=json_output):
        if can_launch_cli_wizard():
            run_cli_wizard(initial_flow="sync", target=target)
            return

    if lock_path is None:
        _exit_for_missing_lock_option()
        raise AssertionError("unreachable")
    sync_lock_path = lock_path

    workflow_service = _build_workflow_service()

    try:
        with capture_cli_telemetry() as telemetry:
            result = _run_with_activity(
                "Syncing locked resolver skills",
                lambda: _sync_result(
                    workflow_service,
                    lock_path=sync_lock_path,
                    target=target,
                ),
                show_bar=not json_output,
            )
    except AptitudeResolverError as exc:
        _emit_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _emit_unexpected_error(exc)
        raise typer.Exit(code=1) from exc

    _render_operation_telemetry("Sync", telemetry)

    if json_output:
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    if _has_interactive_output():
        _stdout_console().print(_render_sync_success_panel(sync_lock_path, result))
        return

    typer.echo(_format_sync_success(sync_lock_path, result))


@app.command(help=build_command_help("manifest"))
def manifest() -> None:
    """Show the complete Aptitude CLI capability map."""

    if _has_interactive_output():
        _stdout_console().print(_render_manifest_panel())
        return

    typer.echo(build_manifest_text())


@app.command(help=build_command_help("demo"))
def demo() -> None:
    """Show a presentation-ready overview of the CLI surface."""

    if _has_interactive_output():
        _stdout_console().print(_render_demo_panel())
        return

    typer.echo(_format_demo_text())


@policy_app.command("show", help=build_command_help("policy_show"))
def show_policy(
    json_output: bool = typer.Option(
        False,
        "--json",
        help=OPTIONS["policy_json"].help_text,
    ),
) -> None:
    """Show the effective client policy, preferences, and config layers."""

    try:
        report = build_effective_policy_report()
    except AptitudeResolverError as exc:
        _emit_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _emit_unexpected_error(exc)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(report.model_dump_json(indent=2, exclude_none=True))
        return

    if _has_interactive_output():
        _stdout_console().print(_render_policy_report_panel(report))
        return

    typer.echo(_format_policy_report(report))
