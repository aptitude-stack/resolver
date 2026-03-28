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


ROOT_HELP = """Aptitude Client.

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


def _format_error(error: AptitudeClientError) -> str:
    return json.dumps(
        {
            "error": error.to_payload(),
        },
        indent=2,
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

    prompt_capable = _is_interactive()
    result = use_case.execute(
        ResolveQueryRequestDto(
            query=query,
            version=version,
            select_slug=select_slug,
            interaction_mode=None,
            prompt_capable=prompt_capable,
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
            interaction_mode="never",
            prompt_capable=False,
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

    prompt_capable = _is_interactive()
    result = use_case.execute(
        InstallRequestDto(
            query=query,
            version=version,
            select_slug=select_slug,
            target=target,
            interaction_mode=None,
            prompt_capable=prompt_capable,
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
            interaction_mode="never",
            prompt_capable=False,
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

    build_kwargs: dict[str, object] = {}
    if prefer is not None:
        build_kwargs["selection_profile_override"] = prefer
    if interaction_mode is not None:
        build_kwargs["interaction_mode_override"] = interaction_mode
    allow_trust_values = _parse_csv_option(allow_trust, option_name="--allow-trust")
    allow_lifecycle_values = _parse_csv_option(
        allow_lifecycle,
        option_name="--allow-lifecycle",
    )
    if allow_trust_values is not None:
        build_kwargs["allowed_trust_tiers_override"] = allow_trust_values
    if allow_lifecycle_values is not None:
        build_kwargs["allowed_lifecycle_statuses_override"] = allow_lifecycle_values
    if max_tokens is not None:
        build_kwargs["max_token_estimate_override"] = max_tokens
    if max_content_size is not None:
        build_kwargs["max_content_size_bytes_override"] = max_content_size

    close = lambda: None

    try:
        use_case, close = build_resolve_use_case(**build_kwargs)
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

    build_kwargs: dict[str, object] = {}
    if prefer is not None:
        build_kwargs["selection_profile_override"] = prefer
    if interaction_mode is not None:
        build_kwargs["interaction_mode_override"] = interaction_mode
    allow_trust_values = _parse_csv_option(allow_trust, option_name="--allow-trust")
    allow_lifecycle_values = _parse_csv_option(
        allow_lifecycle,
        option_name="--allow-lifecycle",
    )
    if allow_trust_values is not None:
        build_kwargs["allowed_trust_tiers_override"] = allow_trust_values
    if allow_lifecycle_values is not None:
        build_kwargs["allowed_lifecycle_statuses_override"] = allow_lifecycle_values
    if max_tokens is not None:
        build_kwargs["max_token_estimate_override"] = max_tokens
    if max_content_size is not None:
        build_kwargs["max_content_size_bytes_override"] = max_content_size

    close = lambda: None

    try:
        use_case, close = build_install_use_case(**build_kwargs)
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
