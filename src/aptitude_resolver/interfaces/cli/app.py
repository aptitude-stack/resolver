"""Typer application for the Aptitude CLI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys
from typing import Literal, TypeVar

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
    build_inspect_use_case,
    build_resolve_use_case,
    build_search_use_case,
    build_sync_use_case,
)
from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    EffectivePolicyReportDto,
    InspectSkillRequestDto,
    InspectSkillResultDto,
    InstallResultDto,
    ResolveQueryResultDto,
    SearchSkillsRequestDto,
    SearchSkillsResultDto,
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
    render_cli_error_panel,
    resolve_cli_version,
)
from aptitude_resolver.interfaces.shared import (
    InteractionMode,
    InstallWorkflowOptions,
    InstallWorkflowService,
)
from aptitude_resolver.shared.config import (
    normalize_agent_list,
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
        "search": "search",
        "inspect": "inspect",
        "install": "install",
        "sync": "sync",
        "manifest": "manifest",
        "mcp": "mcp",
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


@app.command(help=build_command_help("mcp"))
def mcp() -> None:
    """Run the local stdio MCP server."""

    from aptitude_resolver.interfaces.mcp.main import main as run_mcp_server

    run_mcp_server()


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


def _format_candidate_line(candidate: DiscoveryCandidateDto) -> str:
    labels = ", ".join(candidate.matched_labels or candidate.labels[:4])
    label_suffix = f" [{labels}]" if labels else ""
    details = [
        candidate.runtime or "unknown runtime",
        candidate.trust_tier,
        candidate.lifecycle_status,
    ]
    if candidate.token_estimate is not None:
        details.append(f"tokens={candidate.token_estimate}")
    if candidate.content_size_bytes is not None:
        details.append(f"size={candidate.content_size_bytes}B")
    prefix = (
        f"{candidate.ranking_position}. "
        if candidate.ranking_position is not None
        else "- "
    )
    return (
        f"{prefix}{candidate.slug}@{candidate.version} - {candidate.name} "
        f"({', '.join(details)}){label_suffix}"
    )


def _candidate_tags(candidate: DiscoveryCandidateDto) -> str:
    """Return the most useful human-facing labels for one candidate."""

    return ", ".join(candidate.matched_labels or candidate.tags or candidate.labels) or "-"


def _candidate_runtime(candidate: DiscoveryCandidateDto) -> str:
    return candidate.runtime or "unknown"


def _format_candidate_stats(candidate: DiscoveryCandidateDto) -> str:
    stats: list[str] = []
    if candidate.token_estimate is not None:
        stats.append(f"{candidate.token_estimate} tokens")
    if candidate.content_size_bytes is not None:
        stats.append(f"{candidate.content_size_bytes} B")
    return " | ".join(stats) or "-"


def _format_published_at(value: str | None) -> str:
    return value or "unknown"


def _format_search_result(result: SearchSkillsResultDto) -> str:
    separator = _text_separator(sys.stdout)
    lines = [
        "Search Results",
        separator,
        f"Query: {result.requested_query}",
    ]
    if not result.candidates:
        lines.append("No candidates returned.")
        return "\n".join(lines)

    lines.append("")
    lines.extend(_format_candidate_line(candidate) for candidate in result.candidates)
    lines.extend(
        [
            "",
            "Next steps:",
            f'  aptitude inspect "{result.requested_query}" --select-slug SLUG',
            f'  aptitude install "{result.requested_query}" --select-slug SLUG',
        ]
    )
    return "\n".join(lines)


def _render_search_result_panel(result: SearchSkillsResultDto) -> Group:
    panel_box = _panel_box_for_stream(sys.stdout)

    summary = Table.grid(expand=True, padding=(0, 2))
    summary.add_column(style=THEME.text_subtle, ratio=1)
    summary.add_column(style=THEME.text_primary, ratio=3)
    summary.add_row("Query", result.requested_query)
    summary.add_row(
        "Matches",
        f"{len(result.candidates)} ranked skill"
        f"{'s' if len(result.candidates) != 1 else ''}",
    )

    candidates = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=panel_box,
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    candidates.add_column("#", style=THEME.text_subtle, min_width=3, no_wrap=True)
    candidates.add_column("Skill", style=THEME.text_primary, min_width=22)
    candidates.add_column("Version", style=THEME.text_subtle, min_width=14, no_wrap=True)
    candidates.add_column("Runtime", style=THEME.text_body, min_width=10, no_wrap=True)
    candidates.add_column("Trust", style=THEME.text_body, min_width=10, no_wrap=True)
    candidates.add_column("Lifecycle", style=THEME.text_body, min_width=10, no_wrap=True)
    candidates.add_column("Stats", style=THEME.text_subtle, ratio=1)
    candidates.add_column("Tags", style=THEME.text_body, ratio=2)
    for index, candidate in enumerate(result.candidates, start=1):
        rank = candidate.ranking_position or index
        candidates.add_row(
            str(rank),
            f"{candidate.slug}\n{candidate.name}",
            candidate.version,
            _candidate_runtime(candidate),
            candidate.trust_tier,
            candidate.lifecycle_status,
            _format_candidate_stats(candidate),
            _candidate_tags(candidate),
        )

    panels: list[Panel] = [
        Panel(
            summary,
            title="Search Summary",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        )
    ]
    if result.candidates:
        panels.append(
            Panel(
                candidates,
                title="Ranked Candidates",
                border_style=THEME.border_secondary,
                box=panel_box,
                padding=(1, 1),
            )
        )
        panels.append(
            Panel(
                Text(
                    "\n".join(
                        [
                            f'aptitude inspect "{result.requested_query}" --select-slug SLUG',
                            f'aptitude install "{result.requested_query}" --select-slug SLUG',
                        ]
                    ),
                    style=THEME.text_body,
                ),
                title="Next Steps",
                border_style=THEME.border_secondary,
                box=panel_box,
                padding=(1, 1),
            )
        )
    else:
        panels.append(
            Panel(
                Text("No candidates returned.", style=THEME.text_body),
                title="Ranked Candidates",
                border_style=THEME.border_secondary,
                box=panel_box,
                padding=(1, 1),
            )
        )
    return Group(*panels)


def _format_inspect_result(result: InspectSkillResultDto) -> str:
    separator = _text_separator(sys.stdout)
    lines = [
        "Skill Inspection",
        separator,
        f"Query: {result.requested_query}",
    ]
    if result.status == "selection_required":
        lines.extend(["", "Selection required. Matching candidates:"])
        lines.extend(_format_candidate_line(candidate) for candidate in result.candidates)
        return "\n".join(lines)

    if result.selected_coordinate is not None:
        lines.append(
            "Selected: "
            f"{result.selected_coordinate.slug}@{result.selected_coordinate.version}"
        )

    if result.skill is not None:
        skill = result.skill
        lines.extend(
            [
                "",
                "Metadata",
                separator,
                f"Name: {skill.name}",
                f"Description: {skill.description}",
                f"Runtime: {skill.runtime or 'unknown'}",
                f"Lifecycle: {skill.lifecycle_status}",
                f"Trust: {skill.trust_tier}",
                f"Tokens: {_format_policy_limit(skill.token_estimate)}",
                f"Content size: {_format_policy_limit(skill.content_size_bytes)} bytes",
            ]
        )
        if skill.content_checksum_algorithm and skill.content_checksum_digest:
            lines.append(
                "Checksum: "
                f"{skill.content_checksum_algorithm}:{skill.content_checksum_digest}"
            )

    if result.available_versions:
        lines.extend(["", "Available Versions", separator])
        for item in result.available_versions:
            default_suffix = " default" if item.is_current_default else ""
            lines.append(
                f"- {item.version} ({item.lifecycle_status}, {item.trust_tier})"
                f"{default_suffix}"
            )

    if result.content_preview is not None:
        suffix = " (truncated)" if result.content_preview_truncated else ""
        lines.extend(["", f"Content Preview{suffix}", separator, result.content_preview])

    return "\n".join(lines)


def _skill_description(result: InspectSkillResultDto) -> str:
    if result.skill is None:
        return "No description available."
    return result.skill.description or result.skill.rendered_summary or "No description available."


def _render_inspect_selection_required_panel(result: InspectSkillResultDto) -> Group:
    panel_box = _panel_box_for_stream(sys.stdout)
    candidates = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=panel_box,
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    candidates.add_column("#", style=THEME.text_subtle, min_width=3, no_wrap=True)
    candidates.add_column("Skill", style=THEME.text_primary, min_width=22)
    candidates.add_column("Version", style=THEME.text_subtle, min_width=14, no_wrap=True)
    candidates.add_column("Runtime", style=THEME.text_body, min_width=10, no_wrap=True)
    candidates.add_column("Trust", style=THEME.text_body, min_width=10, no_wrap=True)
    candidates.add_column("Tags", style=THEME.text_body, ratio=2)
    for index, candidate in enumerate(result.candidates, start=1):
        candidates.add_row(
            str(candidate.ranking_position or index),
            f"{candidate.slug}\n{candidate.name}",
            candidate.version,
            _candidate_runtime(candidate),
            candidate.trust_tier,
            _candidate_tags(candidate),
        )
    return Group(
        Panel(
            Text(
                f"Query: {result.requested_query}\n"
                "Multiple matching skills require an explicit selection.",
                style=THEME.text_body,
            ),
            title="Skill Inspection",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        ),
        Panel(
            candidates,
            title="Matching Candidates",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        ),
        Panel(
            Text(
                f'aptitude inspect "{result.requested_query}" --select-slug SLUG',
                style=THEME.text_body,
            ),
            title="Next Step",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        ),
    )


def _render_inspect_result_panel(result: InspectSkillResultDto) -> Group:
    if result.status == "selection_required":
        return _render_inspect_selection_required_panel(result)

    panel_box = _panel_box_for_stream(sys.stdout)
    summary = Table.grid(expand=True, padding=(0, 2))
    summary.add_column(style=THEME.text_subtle, ratio=1)
    summary.add_column(style=THEME.text_primary, ratio=3)
    summary.add_row("Query", result.requested_query)
    if result.selected_coordinate is not None:
        summary.add_row(
            "Selected",
            f"{result.selected_coordinate.slug} ({result.selected_coordinate.version})",
        )
    if result.skill is not None:
        summary.add_row("Name", result.skill.name)
        summary.add_row("Description", _skill_description(result))

    metadata = Table.grid(expand=True, padding=(0, 2))
    metadata.add_column(style=THEME.text_subtle, ratio=1)
    metadata.add_column(style=THEME.text_primary, ratio=3)
    if result.skill is not None:
        skill = result.skill
        metadata.add_row("Runtime", skill.runtime or "unknown")
        metadata.add_row("Trust", skill.trust_tier)
        metadata.add_row("Lifecycle", skill.lifecycle_status)
        metadata.add_row("Tags", ", ".join(skill.tags) if skill.tags else "-")
        metadata.add_row("Tokens", _format_policy_limit(skill.token_estimate))
        metadata.add_row("Size", f"{_format_policy_limit(skill.content_size_bytes)} bytes")
        metadata.add_row("Published", _format_published_at(skill.published_at))
        if skill.content_checksum_algorithm and skill.content_checksum_digest:
            metadata.add_row(
                "Checksum",
                f"{skill.content_checksum_algorithm}:{skill.content_checksum_digest}",
            )

    versions = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=panel_box,
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    versions.add_column("Version", style=THEME.text_primary, min_width=14, no_wrap=True)
    versions.add_column("Default", style=THEME.text_subtle, min_width=8, no_wrap=True)
    versions.add_column("Trust", style=THEME.text_body, min_width=10, no_wrap=True)
    versions.add_column("Lifecycle", style=THEME.text_body, min_width=10, no_wrap=True)
    versions.add_column("Published", style=THEME.text_subtle, ratio=1)
    for item in result.available_versions:
        versions.add_row(
            item.version,
            "yes" if item.is_current_default else "",
            item.trust_tier,
            item.lifecycle_status,
            _format_published_at(item.published_at),
        )

    preview_text = result.content_preview or "No markdown preview returned."
    if result.content_preview_truncated:
        preview_text = f"{preview_text}\n\nPreview truncated for terminal display."

    panels: list[Panel] = [
        Panel(
            summary,
            title="Skill Inspection",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        )
    ]
    if result.skill is not None:
        panels.append(
            Panel(
                metadata,
                title="Metadata",
                border_style=THEME.border_secondary,
                box=panel_box,
                padding=(1, 1),
            )
        )
    if result.available_versions:
        panels.append(
            Panel(
                versions,
                title="Available Versions",
                border_style=THEME.border_secondary,
                box=panel_box,
                padding=(1, 1),
            )
        )
    panels.append(
        Panel(
            Text(preview_text, style=THEME.text_body),
            title="Markdown Preview",
            border_style=THEME.border_secondary,
            box=panel_box,
            padding=(1, 1),
        )
    )
    return Group(*panels)


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

    if result.exported_skills:
        lines.append(separator)
        lines.append("Exported agent skills:")
        for item in result.exported_skills:
            lines.append(f"  {item.agent}: {item.destination_path}")

    if result.lock_path:
        lines.append(separator)
        lines.append(f"Lockfile: {result.lock_path}")

    if result.materialized_root:
        lines.append(separator)
        lines.append(f"Aptitude state: {result.materialized_root}")

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
    if result.export_roots:
        summary.add_row(
            "Agent roots",
            ", ".join(f"{agent}: {path}" for agent, path in result.export_roots.items()),
        )
    if result.lock_path:
        summary.add_row("Lockfile", str(result.lock_path))
    if result.materialized_root:
        summary.add_row("Aptitude state", str(result.materialized_root))

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

    exported = Table(
        expand=True,
        show_header=True,
        header_style=THEME.text_muted,
        box=_panel_box_for_stream(sys.stdout),
        border_style=THEME.border_primary,
        pad_edge=False,
    )
    exported.add_column("Agent", style=THEME.text_primary, min_width=14)
    exported.add_column("Skill", style=THEME.text_primary, min_width=18)
    exported.add_column("Path", style=THEME.text_body, ratio=3)
    for exported_skill in result.exported_skills:
        exported.add_row(
            exported_skill.agent,
            exported_skill.slug,
            exported_skill.destination_path,
        )

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
    if result.exported_skills:
        panels.append(
            Panel(
                exported,
                title="Agent Exports",
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
        if selection.candidate_limit is not None:
            lines.append(f"candidates {selection.candidate_limit}")

    policy = layer.policy
    if policy is not None:
        if policy.allowed_trust_tiers is not None:
            lines.append("trust " + _format_policy_list(policy.allowed_trust_tiers))
        if policy.allowed_lifecycle_statuses is not None:
            lines.append(
                "lifecycle "
                + _format_policy_list(policy.allowed_lifecycle_statuses)
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
            "workspace config: no aptitude.toml found upward from "
            f"{line_report.cwd}"
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
        (
            f"candidate limit: {report.effective_selection.candidate_limit} "
            f"(from: {_source_label(report.effective_selection.candidate_limit_source)})"
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
    grid.add_row("Candidates", str(report.effective_selection.candidate_limit))
    grid.add_row(
        "From",
        _source_label(report.effective_selection.candidate_limit_source),
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
    if command_name == "search":
        return (
            "prefer",
            "allow_trust",
            "allow_lifecycle",
            "max_tokens",
            "max_content_size",
            "search_json",
        )
    if command_name == "inspect":
        return (
            "version_select",
            "select_slug",
            "prefer",
            "interaction_mode",
            "allow_trust",
            "allow_lifecycle",
            "max_tokens",
            "max_content_size",
            "preview_chars",
            "inspect_json",
        )
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
            "install_agent",
            "install_scope",
            "install_global",
            "install_export_root",
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
                ["search", "inspect", "install", "sync", "policy", "manifest", "mcp"]
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


def _render_error_panel(message: str) -> Panel:
    return render_cli_error_panel(message, stream=sys.stderr)


def _emit_error_message(message: str) -> None:
    _stderr_console().print(_render_error_panel(message))


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
    target: Path | None,
    agents: list[str],
    scope: str,
    export_root: Path | None,
    cwd: Path | None,
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
            agents=agents,
            scope=_install_scope(scope),
            export_root=export_root,
            cwd=cwd,
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
            agents=agents,
            scope=_install_scope(scope),
            export_root=export_root,
            cwd=cwd,
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
    target: Path | None,
) -> SyncResultDto:
    """Execute sync from one existing lockfile."""

    return workflow_service.sync_lock(lock_path=lock_path, target=target)


def _install_scope(scope: str) -> Literal["project", "global", "custom"]:
    normalized = scope.strip().lower()
    if normalized in {"project", "global", "custom"}:
        return normalized  # type: ignore[return-value]
    raise typer.BadParameter("scope must be project, global, or custom")


def _resolve_cli_install_scope(
    *,
    scope: str | None,
    global_install: bool,
    export_root: Path | None,
) -> Literal["project", "global", "custom"]:
    if scope is not None and global_install:
        raise typer.BadParameter("Use either --scope global or --global, not both.")
    if scope is not None:
        return _install_scope(scope)
    if global_install:
        return "global"
    if export_root is not None:
        return "custom"
    return "project"


def _resolve_cli_agents(agent: list[str] | None) -> list[str]:
    try:
        return normalize_agent_list(agent or ["codex"])
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


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
    agent: list[str] | None,
    scope: str | None,
    global_install: bool,
    export_root: Path | None,
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
        and agent is None
        and scope is None
        and not global_install
        and export_root is None
        and not json_output
    )


def _can_launch_sync_flow(
    *,
    lock_path: Path | None,
    json_output: bool,
) -> bool:
    """Return whether a bare sync invocation should open the guided flow."""

    return lock_path is None and not json_output


def _search_result(
    *,
    query: str,
    options: InstallWorkflowOptions,
) -> SearchSkillsResultDto:
    """Execute discovery-only search."""

    use_case, close = build_search_use_case(
        selection_profile_override=options.selection_profile,
        interaction_mode_override=options.interaction_mode,
        allowed_trust_tiers_override=options.allowed_trust_tiers,
        allowed_lifecycle_statuses_override=options.allowed_lifecycle_statuses,
        max_token_estimate_override=options.max_token_estimate,
        max_content_size_bytes_override=options.max_content_size_bytes,
    )
    try:
        return use_case.execute(SearchSkillsRequestDto(query=query))
    finally:
        close()


def _inspect_result(
    *,
    query: str,
    version: str | None,
    select_slug: str | None,
    preview_chars: int,
    options: InstallWorkflowOptions,
    json_output: bool,
) -> InspectSkillResultDto:
    """Execute selected-skill inspection and complete interactive selection."""

    use_case, close = build_inspect_use_case(
        selection_profile_override=options.selection_profile,
        interaction_mode_override=options.interaction_mode,
        allowed_trust_tiers_override=options.allowed_trust_tiers,
        allowed_lifecycle_statuses_override=options.allowed_lifecycle_statuses,
        max_token_estimate_override=options.max_token_estimate,
        max_content_size_bytes_override=options.max_content_size_bytes,
    )
    try:
        result = use_case.execute(
            InspectSkillRequestDto(
                query=query,
                version=version,
                select_slug=select_slug,
                interaction_mode=options.interaction_mode,
                prompt_capable=_can_prompt_user() and not json_output,
                preview_char_limit=preview_chars,
            )
        )
        if result.status == "selection_required" and not json_output:
            chosen_slug = _prompt_for_candidate_slug(result.candidates)
            return use_case.execute(
                InspectSkillRequestDto(
                    query=query,
                    version=version,
                    select_slug=chosen_slug,
                    interaction_mode="never",
                    prompt_capable=False,
                    selection_source="interactive",
                    preview_char_limit=preview_chars,
                )
            )
        return result
    finally:
        close()


@app.command(help=build_command_help("search"))
def search(
    query: str,
    prefer: str | None = typer.Option(
        None,
        "--prefer",
        help=OPTIONS["prefer"].help_text,
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
    json_output: bool = typer.Option(
        False,
        "--json",
        help=OPTIONS["search_json"].help_text,
    ),
) -> None:
    """Search registry candidates without resolving or installing."""

    options = build_workflow_options(
        prefer=prefer,
        allow_trust=allow_trust,
        allow_lifecycle=allow_lifecycle,
        max_tokens=max_tokens,
        max_content_size=max_content_size,
    )

    try:
        result = _run_with_activity(
            "Searching resolver skills",
            lambda: _search_result(query=query, options=options),
        )
    except AptitudeResolverError as exc:
        _emit_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _emit_unexpected_error(exc)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    if _has_interactive_output():
        _stdout_console().print(_render_search_result_panel(result))
        return

    typer.echo(_format_search_result(result))


@app.command(help=build_command_help("inspect"))
def inspect(
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
    preview_chars: int = typer.Option(
        4000,
        "--preview-chars",
        min=0,
        help=OPTIONS["preview_chars"].help_text,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=OPTIONS["inspect_json"].help_text,
    ),
) -> None:
    """Inspect one skill candidate without resolving or installing."""

    options = build_workflow_options(
        prefer=prefer,
        interaction_mode=interaction_mode,
        allow_trust=allow_trust,
        allow_lifecycle=allow_lifecycle,
        max_tokens=max_tokens,
        max_content_size=max_content_size,
    )

    try:
        result = _run_with_activity(
            "Inspecting resolver skill",
            lambda: _inspect_result(
                query=query,
                version=version,
                select_slug=select_slug,
                preview_chars=preview_chars,
                options=options,
                json_output=json_output,
            ),
        )
    except AptitudeResolverError as exc:
        _emit_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _emit_unexpected_error(exc)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    if _has_interactive_output():
        _stdout_console().print(_render_inspect_result_panel(result))
        return

    typer.echo(_format_inspect_result(result))


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
    agent: list[str] | None = typer.Option(
        None,
        "--agent",
        help=OPTIONS["install_agent"].help_text,
    ),
    scope: str | None = typer.Option(
        None,
        "--scope",
        help=OPTIONS["install_scope"].help_text,
    ),
    global_install: bool = typer.Option(
        False,
        "--global",
        help=OPTIONS["install_global"].help_text,
    ),
    export_root: Path | None = typer.Option(
        None,
        "--export-root",
        help=OPTIONS["install_export_root"].help_text,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help=OPTIONS["install_json"].help_text,
    ),
) -> None:
    """Install a skill query into one or more agent skill roots."""

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
        agent=agent,
        scope=scope,
        global_install=global_install,
        export_root=export_root,
        json_output=json_output,
    ):
        if can_launch_cli_wizard():
            if query is None:
                run_cli_wizard(initial_flow="install")
            else:
                run_cli_wizard(
                    initial_flow="install",
                    initial_query=query,
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
    install_agents = _resolve_cli_agents(agent)
    install_scope = _resolve_cli_install_scope(
        scope=scope,
        global_install=global_install,
        export_root=export_root,
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
                    target=None,
                    agents=install_agents,
                    scope=install_scope,
                    export_root=export_root,
                    cwd=Path.cwd(),
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
    target: Path | None = typer.Option(
        None,
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
