"""Typer application for the Aptitude CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import typer

from aptitude_resolver.application.composition import (
    build_install_use_case,
    build_resolve_use_case,
    build_sync_use_case,
)
from aptitude_resolver.application.dto import (
    DiscoveryCandidateDto,
    InstallResultDto,
    ResolveQueryResultDto,
    SyncResultDto,
)
from aptitude_resolver.domain.errors import AptitudeResolverError
from aptitude_resolver.interfaces.shared import (
    InteractionMode,
    InstallWorkflowOptions,
    InstallWorkflowService,
)


ROOT_HELP = """Aptitude Resolver.

Deterministic client for discovering, resolving, locking, and materializing AI skills.

Public commands:
  install  fresh planning from a query and local materialization
  sync     replay and materialize from an existing lockfile

Required environment:
  APTITUDE_SERVER_BASE_URL   registry base URL
  APTITUDE_READ_TOKEN        registry read token

Examples:
  aptitude install "Postman Primary Skill"
  aptitude install "Postman" --interaction-mode always
  aptitude install "Postman Primary Skill" --prefer low-cost
  aptitude sync --lock aptitude.lock.json

Use `install --help` or `sync --help` for command-specific options."""

INSTALL_HELP = """Install a skill query into a local demo workspace.

Fresh planning flow:
  discovery -> resolver -> governance -> lockfile -> execution

Common examples:
  aptitude install "Postman Primary Skill"
  aptitude install "Postman" --interaction-mode always
  aptitude install "Postman Primary Skill" --prefer low-cost
  aptitude install "Postman Primary Skill" --json

Selection behavior:
  --select-slug       bypasses ambiguity by choosing one discovered candidate
  --prefer            ranks legal candidates with balanced, low-cost, or high-trust
  --interaction-mode  controls root ambiguity: auto, always, or never

Policy behavior:
  --allow-trust         restricts allowed trust tiers for fresh planning
  --allow-lifecycle     restricts allowed lifecycle statuses for fresh planning
  --max-tokens          rejects skills above a token ceiling
  --max-content-size    rejects skills above a content-size ceiling

Output behavior:
  default   human-friendly install summary
  --json    structured machine-readable result"""

SYNC_HELP = """Materialize a locked system from an existing lockfile.

Lock replay path:
  lock parse + replay -> execution planning -> materialization

Common examples:
  aptitude sync --lock aptitude.lock.json
  aptitude sync --lock aptitude.lock.json --target demo_postman
  aptitude sync --lock aptitude.lock.json --json

Behavior:
  uses the existing lockfile as the source of truth
  does not call discovery or resolver
  rebuilds the local workspace from locked data only"""

RESOLVE_HELP = """Resolve a skill query and print a stable JSON result.

Fresh planning flow:
  discovery -> resolver -> governance -> lockfile -> execution planning

Common examples:
  aptitude resolve "Postman Primary Skill"
  aptitude resolve "Postman" --interaction-mode never
  aptitude resolve "Postman Primary Skill" --prefer high-trust
  aptitude resolve "Postman Primary Skill" --allow-trust verified,internal

This is the hidden preview/debug surface. It follows the same planning path as install,
but stops after planning and prints the result instead of materializing it."""

app = typer.Typer(no_args_is_help=True, help=ROOT_HELP)


@app.callback()
def main() -> None:
    """Aptitude CLI root command group."""


def _format_error(error: AptitudeResolverError) -> str:
    return json.dumps(
        {
            "error": error.to_payload(),
        },
        indent=2,
    )


def _build_workflow_service() -> InstallWorkflowService:
    """Create one workflow service using the current builder functions."""

    return InstallWorkflowService(
        resolve_builder=build_resolve_use_case,
        install_builder=build_install_use_case,
        sync_builder=build_sync_use_case,
    )


def _parse_csv_option(
    value: str | None,
    *,
    option_name: str,
) -> list[str] | None:
    """Parse one comma-separated CLI option into trimmed values."""

    if value is None:
        return None
    items = [item.strip() for item in value.split(",")]
    if any(not item for item in items):
        raise typer.BadParameter(
            f"{option_name} must be a comma-separated list without empty values."
        )
    deduplicated: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduplicated.append(item)
    return deduplicated


def _parse_interaction_mode(value: str | None) -> InteractionMode | None:
    """Validate one CLI interaction mode string."""

    if value is None:
        return None
    if value not in {"auto", "always", "never"}:
        raise typer.BadParameter(
            "--interaction-mode must be one of: auto, always, never."
        )
    return cast(InteractionMode, value)


def _is_interactive() -> bool:
    """Return whether the CLI can safely prompt the user."""

    return sys.stdin.isatty() and sys.stdout.isatty()


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

    resolved_coordinates = [
        (skill.slug, skill.version) for skill in result.installed_skills
    ]
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


@app.command(hidden=True, help=RESOLVE_HELP)
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
    prefer: str | None = typer.Option(
        None,
        "--prefer",
        help="Selection profile for choosing among legal candidates: balanced, low-cost, or high-trust.",
    ),
    interaction_mode: str | None = typer.Option(
        None,
        "--interaction-mode",
        help="How root ambiguity should be handled: auto, always, or never.",
    ),
    allow_trust: str | None = typer.Option(
        None,
        "--allow-trust",
        help="Comma-separated allowed trust tiers for fresh planning.",
    ),
    allow_lifecycle: str | None = typer.Option(
        None,
        "--allow-lifecycle",
        help="Comma-separated allowed lifecycle statuses for fresh planning.",
    ),
    max_tokens: int | None = typer.Option(
        None,
        "--max-tokens",
        min=0,
        help="Reject candidates and resolved graphs above this token ceiling.",
    ),
    max_content_size: int | None = typer.Option(
        None,
        "--max-content-size",
        min=0,
        help="Reject candidates and resolved graphs above this content-size ceiling in bytes.",
    ),
) -> None:
    """Resolve a skill query and print a stable JSON result."""

    allow_trust_values = _parse_csv_option(allow_trust, option_name="--allow-trust")
    allow_lifecycle_values = _parse_csv_option(
        allow_lifecycle,
        option_name="--allow-lifecycle",
    )
    options = InstallWorkflowOptions(
        selection_profile=prefer,
        interaction_mode=_parse_interaction_mode(interaction_mode),
        allowed_trust_tiers=allow_trust_values,
        allowed_lifecycle_statuses=allow_lifecycle_values,
        max_token_estimate=max_tokens,
        max_content_size_bytes=max_content_size,
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

    typer.echo(result.model_dump_json(indent=2, exclude_none=True))


@app.command(help=INSTALL_HELP)
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
    prefer: str | None = typer.Option(
        None,
        "--prefer",
        help="Selection profile for choosing among legal candidates: balanced, low-cost, or high-trust.",
    ),
    interaction_mode: str | None = typer.Option(
        None,
        "--interaction-mode",
        help="How root ambiguity should be handled: auto, always, or never.",
    ),
    allow_trust: str | None = typer.Option(
        None,
        "--allow-trust",
        help="Comma-separated allowed trust tiers for fresh planning.",
    ),
    allow_lifecycle: str | None = typer.Option(
        None,
        "--allow-lifecycle",
        help="Comma-separated allowed lifecycle statuses for fresh planning.",
    ),
    max_tokens: int | None = typer.Option(
        None,
        "--max-tokens",
        min=0,
        help="Reject candidates and resolved graphs above this token ceiling.",
    ),
    max_content_size: int | None = typer.Option(
        None,
        "--max-content-size",
        min=0,
        help="Reject candidates and resolved graphs above this content-size ceiling in bytes.",
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

    allow_trust_values = _parse_csv_option(allow_trust, option_name="--allow-trust")
    allow_lifecycle_values = _parse_csv_option(
        allow_lifecycle,
        option_name="--allow-lifecycle",
    )
    options = InstallWorkflowOptions(
        selection_profile=prefer,
        interaction_mode=_parse_interaction_mode(interaction_mode),
        allowed_trust_tiers=allow_trust_values,
        allowed_lifecycle_statuses=allow_lifecycle_values,
        max_token_estimate=max_tokens,
        max_content_size_bytes=max_content_size,
    )

    try:
        workflow_service = _build_workflow_service()
        result = _install_result(
            workflow_service,
            query=query,
            version=version,
            select_slug=select_slug,
            target=target,
            options=options,
        )
    except AptitudeResolverError as exc:
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output or result.status != "installed":
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    typer.echo(_format_install_success(result))


@app.command(help=SYNC_HELP)
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

    workflow_service = _build_workflow_service()

    try:
        result = _sync_result(
            workflow_service,
            lock_path=lock_path,
            target=target,
        )
    except AptitudeResolverError as exc:
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(result.model_dump_json(indent=2, exclude_none=True))
        return

    typer.echo(_format_sync_success(lock_path, result))
