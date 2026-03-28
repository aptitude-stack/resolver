"""Typer application for the Aptitude CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from aptitude_client.application.composition import (
    build_install_use_case,
    build_resolve_use_case,
    build_sync_use_case,
)
from aptitude_client.application.dto import (
    DiscoveryCandidateDto,
    InstallRequestDto,
    InstallResultDto,
    ResolveQueryRequestDto,
    ResolveQueryResultDto,
    SyncRequestDto,
    SyncResultDto,
)
from aptitude_client.application.use_cases import (
    InstallSkillUseCase,
    ResolveSkillQueryUseCase,
    SyncFromLockUseCase,
)
from aptitude_client.domain.errors import AptitudeClientError


app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Aptitude CLI root command group."""


def _format_error(error: AptitudeClientError) -> str:
    return json.dumps(
        {
            "error": error.to_payload(),
        },
        indent=2,
    )


def _is_interactive() -> bool:
    """Return whether the CLI can safely prompt the user."""

    return sys.stdin.isatty() and sys.stdout.isatty()


def _render_candidate(index: int, candidate: DiscoveryCandidateDto) -> str:
    """Render one candidate line for interactive selection."""

    labels = ", ".join(candidate.matched_labels or candidate.labels[:4])
    label_suffix = f" [{labels}]" if labels else ""
    return (
        f"{index}. {candidate.slug}@{candidate.version} - {candidate.name}"
        f" ({candidate.runtime or 'unknown runtime'}, {candidate.trust_tier}, {candidate.lifecycle_status})"
        f"{label_suffix}"
    )


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


def _format_install_success(result: InstallResultDto) -> str:
    """Render a human-friendly install summary inspired by package managers."""

    lines = [f"Collecting {result.requested_query}"]

    if result.selected_coordinate is not None:
        lines.append(
            "  Using aptitude candidate "
            f"{result.selected_coordinate.slug} ({result.selected_coordinate.version})"
        )

    resolved_coordinates = _resolved_install_coordinates(result)
    selected_slug = result.selected_coordinate.slug if result.selected_coordinate is not None else None
    dependency_coordinates = [
        coordinate for coordinate in resolved_coordinates if coordinate[0] != selected_slug
    ]
    for dependency_slug, dependency_version in dependency_coordinates:
        lines.append(f"Collecting dependency {dependency_slug} ({dependency_version})")

    if resolved_coordinates:
        lines.append(
            "Installing collected aptitude skills: "
            + ", ".join(slug for slug, _ in resolved_coordinates)
        )
        lines.append(
            "Successfully installed "
            + " ".join(f"{slug}-{version}" for slug, version in resolved_coordinates)
        )

    if result.materialized_root:
        lines.append(f"Installed to: {result.materialized_root}")

    return "\n".join(lines)


def _format_sync_success(lock_path: Path, result: SyncResultDto) -> str:
    """Render a human-friendly sync summary inspired by package managers."""

    resolved_coordinates = [(skill.slug, skill.version) for skill in result.installed_skills]
    lines = [f"Syncing locked aptitude skills from {lock_path.resolve()}"]
    if resolved_coordinates:
        lines.append(
            "Installing locked aptitude skills: "
            + ", ".join(slug for slug, _ in resolved_coordinates)
        )
        lines.append(
            "Successfully synced "
            + " ".join(f"{slug}-{version}" for slug, version in resolved_coordinates)
        )
    if result.materialized_root:
        lines.append(f"Installed to: {result.materialized_root}")
    return "\n".join(lines)


def _resolve_query_result(
    use_case: ResolveSkillQueryUseCase,
    *,
    query: str,
    version: str | None,
    select_slug: str | None,
) -> ResolveQueryResultDto:
    """Execute resolve and, if needed, complete interactive candidate selection."""

    interactive = _is_interactive() and select_slug is None
    result = use_case.execute(
        ResolveQueryRequestDto(
            query=query,
            version=version,
            select_slug=select_slug,
            interactive=interactive,
        )
    )
    if result.status != "selection_required":
        return result

    chosen_slug = _prompt_for_candidate_slug(result.candidates)
    return use_case.execute(
        ResolveQueryRequestDto(
            query=query,
            version=version,
            select_slug=chosen_slug,
            interactive=False,
            selection_source="interactive",
        )
    )


def _install_result(
    use_case: InstallSkillUseCase,
    *,
    query: str,
    version: str | None,
    select_slug: str | None,
    target: Path,
) -> InstallResultDto:
    """Execute install and, if needed, complete interactive candidate selection."""

    interactive = _is_interactive() and select_slug is None
    result = use_case.execute(
        InstallRequestDto(
            query=query,
            version=version,
            select_slug=select_slug,
            target=target,
            interactive=interactive,
        )
    )
    if result.status != "selection_required":
        return result

    chosen_slug = _prompt_for_candidate_slug(result.candidates)
    return use_case.execute(
        InstallRequestDto(
            query=query,
            version=version,
            select_slug=chosen_slug,
            target=target,
            interactive=False,
            selection_source="interactive",
        )
    )


def _sync_result(
    use_case: SyncFromLockUseCase,
    *,
    lock_path: Path,
    target: Path,
) -> SyncResultDto:
    """Execute sync from one existing lockfile."""

    return use_case.execute(
        SyncRequestDto(
            lock_path=lock_path,
            target=target,
        )
    )


@app.command(hidden=True)
def resolve(
    query: str,
    version: str | None = typer.Option(
        None,
        "--version",
        help="Optional exact immutable version. When omitted, the client selects a version deterministically.",
    ),
    select_slug: str | None = typer.Option(
        None,
        "--select-slug",
        help="Explicitly pick one discovered slug without prompting.",
    ),
) -> None:
    """Resolve a skill query and print a stable JSON result."""

    use_case, close = build_resolve_use_case()

    try:
        result = _resolve_query_result(
            use_case,
            query=query,
            version=version,
            select_slug=select_slug,
        )
    except AptitudeClientError as exc:
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        close()

    typer.echo(result.model_dump_json(indent=2, exclude_none=True))


@app.command()
def install(
    query: str,
    version: str | None = typer.Option(
        None,
        "--version",
        help="Optional exact immutable version. When omitted, the client selects a version deterministically.",
    ),
    select_slug: str | None = typer.Option(
        None,
        "--select-slug",
        help="Explicitly pick one discovered slug without prompting.",
    ),
    target: Path = typer.Option(
        Path("skill_demo"),
        "--target",
        help="Local directory where the resolved graph should be materialized.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the structured JSON install result for automation and CI.",
    ),
) -> None:
    """Install a skill query into a local demo workspace."""

    use_case, close = build_install_use_case()

    try:
        result = _install_result(
            use_case,
            query=query,
            version=version,
            select_slug=select_slug,
            target=target,
        )
    except AptitudeClientError as exc:
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        close()

    if json_output or result.status != "installed":
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    typer.echo(_format_install_success(result))


@app.command()
def sync(
    lock_path: Path = typer.Option(
        ...,
        "--lock",
        help="Path to an existing aptitude lockfile.",
    ),
    target: Path = typer.Option(
        Path("skill_demo"),
        "--target",
        help="Local directory where the locked system should be materialized.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the structured JSON sync result for automation and CI.",
    ),
) -> None:
    """Materialize a locked system from an existing lockfile."""

    use_case, close = build_sync_use_case()

    try:
        result = _sync_result(
            use_case,
            lock_path=lock_path,
            target=target,
        )
    except AptitudeClientError as exc:
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        close()

    if json_output:
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    typer.echo(_format_sync_success(lock_path, result))
