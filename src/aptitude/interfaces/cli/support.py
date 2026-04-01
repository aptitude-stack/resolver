"""Shared support helpers for the Aptitude CLI surfaces."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import metadata
from typing import cast

import typer

from aptitude import __version__
from aptitude.domain.errors import (
    AptitudeResolverError,
    ContentChecksumMismatchError,
    DiscoveryNoCandidatesError,
    InvalidLockfileError,
    InvalidResolverConfigurationError,
    PolicyViolationError,
    SelectionSlugNotFoundError,
)
from aptitude.interfaces.cli.catalog import HORIZONTAL_SEPARATOR
from aptitude.interfaces.shared import (
    InteractionMode,
    InstallWorkflowOptions,
    InstallWorkflowService,
)
from aptitude.telemetry.metrics import StageTiming


def build_workflow_service(
    *,
    resolve_builder,
    install_builder,
    sync_builder,
) -> InstallWorkflowService:
    """Create one workflow service from the provided builder functions."""

    return InstallWorkflowService(
        resolve_builder=resolve_builder,
        install_builder=install_builder,
        sync_builder=sync_builder,
    )


def build_workflow_options(
    *,
    prefer: str | None = None,
    interaction_mode: str | None = None,
    allow_trust: str | None = None,
    allow_lifecycle: str | None = None,
    max_tokens: int | None = None,
    max_content_size: int | None = None,
) -> InstallWorkflowOptions:
    """Build one validated set of workflow overrides from CLI-style values."""

    return InstallWorkflowOptions(
        selection_profile=prefer,
        interaction_mode=parse_interaction_mode(interaction_mode),
        allowed_trust_tiers=parse_csv_option(allow_trust, option_name="--allow-trust"),
        allowed_lifecycle_statuses=parse_csv_option(
            allow_lifecycle,
            option_name="--allow-lifecycle",
        ),
        max_token_estimate=max_tokens,
        max_content_size_bytes=max_content_size,
    )


@contextmanager
def capture_cli_telemetry() -> Iterator[list[StageTiming]]:
    """Capture stage timings for CLI rendering instead of leaking raw logs."""

    logger = logging.getLogger("aptitude.telemetry")
    original_level = logger.level
    from aptitude.application.queries import plan_skill_resolution
    from aptitude.application.use_cases import install_skill, sync_from_lock
    from aptitude.telemetry import metrics as telemetry_metrics

    original_emitters = [
        (plan_skill_resolution, plan_skill_resolution.emit_stage_timings),
        (install_skill, install_skill.emit_stage_timings),
        (sync_from_lock, sync_from_lock.emit_stage_timings),
        (telemetry_metrics, telemetry_metrics.emit_stage_timings),
    ]
    captured: list[StageTiming] = []

    def _capture_emit_stage_timings(collector, *args: object, **kwargs: object) -> None:
        captured.extend(collector.snapshot())

    try:
        logger.setLevel(max(original_level, logging.WARNING))
        for module, _original in original_emitters:
            module.emit_stage_timings = _capture_emit_stage_timings  # type: ignore[attr-defined]
        yield captured
    finally:
        for module, original in original_emitters:
            module.emit_stage_timings = original  # type: ignore[attr-defined]
        logger.setLevel(original_level)


def format_folded_cli_telemetry(stage_timings: list[StageTiming]) -> str | None:
    """Render one compact folded telemetry summary for human-facing CLI output."""

    if not stage_timings:
        return None

    parts = [f"{timing.stage} {timing.duration_ms:.1f}ms" for timing in stage_timings]
    return "telemetry  " + " | ".join(parts)


def format_cli_error(error: AptitudeResolverError) -> str:
    """Render one CLI-facing error payload."""

    if (
        isinstance(error, InvalidResolverConfigurationError)
        and error.source.lower() == "environment"
    ):
        return format_environment_configuration_error(error)
    if isinstance(error, InvalidResolverConfigurationError):
        return format_invalid_configuration_error(error)
    if isinstance(error, SelectionSlugNotFoundError):
        return format_selection_slug_not_found_error(error)
    if isinstance(error, InvalidLockfileError):
        return format_invalid_lockfile_error(error)
    if isinstance(error, ContentChecksumMismatchError):
        return format_checksum_mismatch_error(error)
    if isinstance(error, DiscoveryNoCandidatesError):
        return format_no_candidates_error(error)
    if isinstance(error, PolicyViolationError):
        return format_policy_violation_error(error)

    return format_generic_cli_error(error)


def format_environment_configuration_error(
    error: InvalidResolverConfigurationError,
) -> str:
    """Render environment setup failures without leaking internal mechanics."""

    missing_variables = parse_missing_environment_variables(error.details)
    lines = ["Aptitude is not configured."]

    if missing_variables:
        lines.append("Set the required environment variables:")
        lines.extend(f"  - {name}" for name in missing_variables)
    else:
        lines.append(error.details)

    lines.extend(["", HORIZONTAL_SEPARATOR, ""])
    lines.append(
        "Export them in your shell or place them in a local .env file, then try again."
    )
    return "\n".join(lines)


def format_invalid_configuration_error(
    error: InvalidResolverConfigurationError,
) -> str:
    """Render one non-environment configuration error for humans."""

    source = error.source.strip().lower()
    if source == "cli override":
        title = "Invalid CLI configuration."
        hint = "Review the supplied flags and try again."
    elif source == "workspace config":
        title = "Invalid workspace configuration."
        hint = "Fix the workspace Aptitude configuration and try again."
    else:
        title = "Invalid resolver configuration."
        hint = "Review the resolver configuration and try again."

    return "\n".join([title, HORIZONTAL_SEPARATOR, error.details, "", hint])


def format_selection_slug_not_found_error(error: SelectionSlugNotFoundError) -> str:
    """Render one invalid explicit-selection error for humans."""

    lines = [
        "Requested selection is not available.",
        f"Query: {error.query}",
        f"Selected slug: {error.selected_slug}",
    ]
    lines.append(HORIZONTAL_SEPARATOR)
    if error.candidates:
        lines.append("Available candidates:")
        lines.extend(f"  - {candidate}" for candidate in error.candidates)
    lines.extend(["", "Choose one of the listed candidates or omit --select-slug."])
    return "\n".join(lines)


def format_invalid_lockfile_error(error: InvalidLockfileError) -> str:
    """Render one lockfile failure for humans."""

    return "\n".join(
        [
            "Lockfile error.",
            HORIZONTAL_SEPARATOR,
            str(error),
            "",
            "Check that --lock points to a valid resolver lockfile and try again.",
        ]
    )


def format_checksum_mismatch_error(error: ContentChecksumMismatchError) -> str:
    """Render one checksum mismatch in a user-friendly format."""

    return "\n".join(
        [
            "Downloaded content failed integrity verification.",
            HORIZONTAL_SEPARATOR,
            f"Skill: {error.slug}@{error.version}",
            f"Algorithm: {error.algorithm}",
            f"Expected digest: {error.expected_digest}",
            f"Actual digest: {error.actual_digest}",
            "",
            "Retry the operation. If it persists, verify the registry artifact.",
        ]
    )


def format_no_candidates_error(error: DiscoveryNoCandidatesError) -> str:
    """Render one no-candidate discovery result for humans."""

    return "\n".join(
        [
            "No matching skills were found.",
            HORIZONTAL_SEPARATOR,
            f"Query: {error.query}",
            "",
            "Try a more specific query or adjust any restrictive policy flags.",
        ]
    )


def format_policy_violation_error(error: PolicyViolationError) -> str:
    """Render one policy rejection for humans."""

    return "\n".join(
        [
            "Policy rejected the requested operation.",
            HORIZONTAL_SEPARATOR,
            str(error),
            "",
            "Adjust the policy flags or workspace configuration and try again.",
        ]
    )


def format_generic_cli_error(error: AptitudeResolverError) -> str:
    """Render one generic resolver error without raw JSON noise."""

    payload = error.to_payload()
    details = [
        f"{humanize_payload_key(key)}: {value}"
        for key, value in payload.items()
        if key not in {"type", "message"} and value not in (None, "", [], {})
    ]
    lines = [friendly_error_title(error), HORIZONTAL_SEPARATOR, str(error)]
    if details:
        lines.extend(["", *details])
    return "\n".join(lines)


def parse_missing_environment_variables(details: str) -> list[str]:
    """Extract missing environment variable names from one settings error."""

    prefix = "Missing required environment variables: "
    if not details.startswith(prefix):
        return []
    names = details.removeprefix(prefix).rstrip(".")
    return [name.strip() for name in names.split(",") if name.strip()]


def parse_csv_option(
    value: str | None,
    *,
    option_name: str,
) -> list[str] | None:
    """Parse one comma-separated CLI option into trimmed unique values."""

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


def parse_interaction_mode(value: str | None) -> InteractionMode | None:
    """Validate one CLI interaction mode string."""

    if value is None:
        return None
    if value not in {"auto", "always", "never"}:
        raise typer.BadParameter(
            "--interaction-mode must be one of: auto, always, never."
        )
    return cast(InteractionMode, value)


def is_interactive() -> bool:
    """Return whether the CLI can safely prompt the user."""

    return sys.stdin.isatty() and sys.stdout.isatty()


def resolve_cli_version() -> str:
    """Return the installed Aptitude version when available."""

    try:
        return metadata.version("aptitude")
    except metadata.PackageNotFoundError:
        return __version__


def format_unexpected_cli_error(error: Exception) -> str:
    """Render one unexpected exception without dumping a traceback."""

    message = str(error).strip()
    if "unable to open database file" in message.lower():
        return "\n".join(
            [
                "Aptitude could not open its local cache.",
                HORIZONTAL_SEPARATOR,
                "",
                "Make sure the cache uses a writable cache directory, then try again.",
            ]
        )

    return "\n".join(
        [
            "Aptitude hit an unexpected internal error.",
            HORIZONTAL_SEPARATOR,
            f"{error.__class__.__name__}: {message or 'no details available'}",
        ]
    )


def friendly_error_title(error: AptitudeResolverError) -> str:
    """Return one short title for a resolver error."""

    raw_name = error.__class__.__name__.removesuffix("Error")
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", raw_name).strip().lower()
    return f"{words.capitalize()}."


def humanize_payload_key(key: str) -> str:
    """Render one payload key as a human-friendly label."""

    return key.replace("_", " ").capitalize()
