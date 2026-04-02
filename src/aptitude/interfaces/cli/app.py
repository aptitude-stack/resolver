"""Typer application for the Aptitude CLI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from aptitude.application.composition import (
    build_install_use_case,
    build_resolve_use_case,
    build_sync_use_case,
)
from aptitude.application.dto import (
    DiscoveryCandidateDto,
    InstallResultDto,
    ResolveQueryResultDto,
    SyncResultDto,
)
from aptitude.domain.errors import (
    AptitudeResolverError,
    InvalidResolverConfigurationError,
)
from aptitude.interfaces.cli.catalog import (
    HORIZONTAL_SEPARATOR,
    OPTIONS,
    THEME,
    build_command_help,
    build_manifest_text,
    build_root_help,
)
from aptitude.interfaces.cli.wizard import run_cli_wizard
from aptitude.interfaces.cli.support import (
    build_workflow_options,
    build_workflow_service as _shared_build_workflow_service,
    capture_cli_telemetry,
    format_cli_error,
    format_cli_install_telemetry_line,
    format_cli_telemetry_block,
    format_unexpected_cli_error,
    is_interactive,
    parse_csv_option,
    parse_interaction_mode,
    parse_missing_environment_variables,
    resolve_cli_version,
)
from aptitude.interfaces.shared import (
    InteractionMode,
    InstallWorkflowOptions,
    InstallWorkflowService,
)

app = typer.Typer(no_args_is_help=True, help=build_root_help())
T = TypeVar("T")
_ACTIVITY_CONSOLE = Console(stderr=True)


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


def _is_interactive() -> bool:
    """Backwards-compatible wrapper for shared TTY detection."""

    return is_interactive()


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

    if not _is_interactive():
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

    if not _is_interactive():
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

    lines = [
        "Installation Summary",
        HORIZONTAL_SEPARATOR,
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
        lines.append(HORIZONTAL_SEPARATOR)
        lines.append(
            "Installing collected resolver skills: "
            + ", ".join(slug for slug, _ in resolved_coordinates)
        )
        lines.append(
            "Successfully installed "
            + " ".join(f"{slug}-{version}" for slug, version in resolved_coordinates)
        )

    if result.materialized_root:
        lines.append(HORIZONTAL_SEPARATOR)
        lines.append(f"Installed to: {result.materialized_root}")

    if telemetry_summary:
        lines.append(HORIZONTAL_SEPARATOR)
        lines.append(telemetry_summary)

    return "\n".join(lines)


def _format_sync_success(lock_path: Path, result: SyncResultDto) -> str:
    """Render a human-friendly sync summary inspired by package managers."""

    resolved_coordinates = [
        (skill.slug, skill.version) for skill in result.installed_skills
    ]
    lines = [
        "Sync summary",
        HORIZONTAL_SEPARATOR,
        f"Syncing locked resolver skills from {lock_path.resolve()}",
    ]
    if resolved_coordinates:
        lines.append(HORIZONTAL_SEPARATOR)
        lines.append(
            "Installing locked resolver skills: "
            + ", ".join(slug for slug, _ in resolved_coordinates)
        )
        lines.append(
            "Successfully synced "
            + " ".join(f"{slug}-{version}" for slug, version in resolved_coordinates)
        )
    if result.materialized_root:
        lines.append(HORIZONTAL_SEPARATOR)
        lines.append(f"Installed to: {result.materialized_root}")
    return "\n".join(lines)


def _resolve_query_result(
    workflow_service: InstallWorkflowService,
    *,
    query: str,
    version: str | None,
    select_slug: str | None,
    options: InstallWorkflowOptions,
) -> ResolveQueryResultDto:
    """Execute resolve and, if needed, complete interactive candidate selection."""

    prompt_capable = _is_interactive()
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

    prompt_capable = _is_interactive()
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
        query is None
        and version is None
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
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(format_unexpected_cli_error(exc), err=True)
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
        run_cli_wizard(initial_flow="install", target=target)
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
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(format_unexpected_cli_error(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output or result.status != "installed":
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
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
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(format_unexpected_cli_error(exc), err=True)
        raise typer.Exit(code=1) from exc

    _render_operation_telemetry("Sync", telemetry)

    if json_output:
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    typer.echo(_format_sync_success(sync_lock_path, result))


@app.command(help=build_command_help("manifest"))
def manifest() -> None:
    """Show the complete Aptitude CLI capability map."""

    typer.echo(build_manifest_text())
