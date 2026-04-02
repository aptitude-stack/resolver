from __future__ import annotations

import logging
from io import StringIO

from aptitude.domain.errors import (
    ContentChecksumMismatchError,
    InvalidResolverConfigurationError,
    InvalidLockfileError,
    SelectionSlugNotFoundError,
)
from aptitude.interfaces.cli import support


def test_build_workflow_options_parses_cli_override_values() -> None:
    options = support.build_workflow_options(
        prefer="low-cost",
        interaction_mode="always",
        allow_trust="verified,internal,verified",
        allow_lifecycle="published,deprecated",
        max_tokens=256,
        max_content_size=4096,
    )

    assert options.selection_profile == "low-cost"
    assert options.interaction_mode == "always"
    assert options.allowed_trust_tiers == ["verified", "internal"]
    assert options.allowed_lifecycle_statuses == ["published", "deprecated"]
    assert options.max_token_estimate == 256
    assert options.max_content_size_bytes == 4096


def test_format_cli_error_renders_environment_configuration_errors_for_humans() -> None:
    rendered = support.format_cli_error(
        InvalidResolverConfigurationError(
            "environment",
            "Missing required environment variables: "
            "APTITUDE_SERVER_BASE_URL, APTITUDE_READ_TOKEN.",
        )
    )

    assert "Aptitude is not configured." in rendered
    assert (
        "────────────────────────────────────────────────────────────────" in rendered
    )
    assert "APTITUDE_SERVER_BASE_URL" in rendered
    assert "APTITUDE_READ_TOKEN" in rendered
    assert ".env" in rendered


def test_format_cli_error_renders_invalid_cli_override_errors_for_humans() -> None:
    rendered = support.format_cli_error(
        InvalidResolverConfigurationError(
            "CLI override", "allowed_trust_tiers contains unknown values: unknown-tier."
        )
    )

    assert "Invalid CLI configuration." in rendered
    assert (
        "────────────────────────────────────────────────────────────────" in rendered
    )
    assert "allowed_trust_tiers contains unknown values: unknown-tier." in rendered
    assert "Review the supplied flags and try again." in rendered


def test_format_cli_error_renders_missing_lockfile_errors_for_humans() -> None:
    rendered = support.format_cli_error(
        InvalidLockfileError("Lockfile not found: /tmp/missing.lock.json")
    )

    assert "Lockfile error." in rendered
    assert (
        "────────────────────────────────────────────────────────────────" in rendered
    )
    assert "Lockfile not found: /tmp/missing.lock.json" in rendered
    assert "--lock points to a valid resolver lockfile" in rendered


def test_format_cli_error_renders_missing_selected_slug_errors_for_humans() -> None:
    rendered = support.format_cli_error(
        SelectionSlugNotFoundError("lint", "missing.skill", ["python.lint", "js.lint"])
    )

    assert "Requested selection is not available." in rendered
    assert (
        "────────────────────────────────────────────────────────────────" in rendered
    )
    assert "Query: lint" in rendered
    assert "Selected slug: missing.skill" in rendered
    assert "python.lint" in rendered
    assert "js.lint" in rendered
    assert "omit --select-slug" in rendered


def test_format_cli_error_renders_checksum_failures_for_humans() -> None:
    rendered = support.format_cli_error(
        ContentChecksumMismatchError(
            slug="python.lint",
            version="1.2.3",
            algorithm="sha256",
            expected_digest="expected",
            actual_digest="actual",
        )
    )

    assert "Downloaded content failed integrity verification." in rendered
    assert (
        "────────────────────────────────────────────────────────────────" in rendered
    )
    assert "Skill: python.lint@1.2.3" in rendered
    assert "Expected digest: expected" in rendered
    assert "Actual digest: actual" in rendered


def test_format_unexpected_error_renders_cache_open_failures_for_humans() -> None:
    rendered = support.format_unexpected_cli_error(
        RuntimeError("unable to open database file")
    )

    assert "Aptitude could not open its local cache." in rendered
    assert (
        "────────────────────────────────────────────────────────────────" in rendered
    )
    assert "writable cache directory" in rendered


def test_format_unexpected_error_renders_generic_failures_without_traceback() -> None:
    rendered = support.format_unexpected_cli_error(RuntimeError("boom"))

    assert "Aptitude hit an unexpected internal error." in rendered
    assert (
        "────────────────────────────────────────────────────────────────" in rendered
    )
    assert "RuntimeError: boom" in rendered


def test_suppress_cli_telemetry_logs_hides_info_events_temporarily() -> None:
    stream = StringIO()
    logger = logging.getLogger("aptitude.telemetry")
    handler = logging.StreamHandler(stream)
    original_level = logger.level
    original_handlers = list(logger.handlers)
    original_propagate = logger.propagate
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    try:
        logger.info("before")
        with support.capture_cli_telemetry():
            logger.info("hidden")
        logger.info("after")
    finally:
        logger.handlers = original_handlers
        logger.propagate = original_propagate
        logger.setLevel(original_level)

    output = stream.getvalue()
    assert "before" in output
    assert "hidden" not in output
    assert "after" in output


def test_format_cli_telemetry_block_renders_one_operation_with_stage_lines() -> None:
    rendered = support.format_cli_telemetry_block(
        "Resolve query",
        [
            support.StageTiming(stage="discovery", duration_ms=95.679),
            support.StageTiming(stage="execution_planning", duration_ms=18.2),
        ]
    )

    assert rendered == "\n".join(
        [
            "Resolve query telemetry",
            "  Discovery           95.7ms",
            "  Execution planning  18.2ms",
        ]
    )
