from __future__ import annotations

import re

from typer.testing import CliRunner

from aptitude_resolver.interfaces.cli import app as app_module


runner = CliRunner()


def test_cli_help_exposes_install_and_sync_as_primary_commands() -> None:
    result = runner.invoke(app_module.app, ["--help"])

    assert result.exit_code == 0
    assert "install" in result.stdout
    assert "sync" in result.stdout
    assert re.search(r"(?m)^\\s*resolve\\s{2,}", result.stdout) is None
    assert "APTITUDE_SERVER_BASE_URL" in result.stdout
    assert "APTITUDE_READ_TOKEN" in result.stdout
    assert "fresh planning from a query and local materialization" in result.stdout
    assert "replay and materialize from an existing lockfile" in result.stdout
    assert 'aptitude install "Postman Primary Skill"' in result.stdout
    assert "aptitude sync --lock aptitude.lock.json" in result.stdout


def test_cli_install_help_exposes_selection_preference_flags() -> None:
    result = runner.invoke(app_module.app, ["install", "--help"])

    assert result.exit_code == 0
    assert "--prefer" in result.stdout
    assert "--interaction-mode" in result.stdout
    assert "--allow-trust" in result.stdout
    assert "--allow-lifecycle" in result.stdout
    assert "--max-tokens" in result.stdout
    assert "--max-content-size" in result.stdout
    assert (
        "discovery -> resolver -> governance -> lockfile -> execution" in result.stdout
    )
    assert "--select-slug" in result.stdout
    assert "--json" in result.stdout
    assert "Common examples" in result.stdout
    assert 'aptitude install "Postman" --interaction-mode always' in result.stdout
    assert "human-friendly install summary" in result.stdout


def test_cli_sync_help_explains_lock_replay_flow() -> None:
    result = runner.invoke(app_module.app, ["sync", "--help"])

    assert result.exit_code == 0
    assert "--lock" in result.stdout
    assert "Lock replay path" in result.stdout
    assert "does not call discovery or resolver" in result.stdout
    assert "uses the existing lockfile as the source of truth" in result.stdout
    assert "aptitude sync --lock aptitude.lock.json --json" in result.stdout
    assert "--allow-trust" not in result.stdout
    assert "--max-tokens" not in result.stdout


def test_hidden_resolve_help_is_rich_even_though_root_help_hides_it() -> None:
    result = runner.invoke(app_module.app, ["resolve", "--help"])

    assert result.exit_code == 0
    assert "Fresh planning flow" in result.stdout
    assert 'aptitude resolve "Postman Primary Skill"' in result.stdout
    assert "--prefer" in result.stdout
    assert "--interaction-mode" in result.stdout
    assert "--allow-trust" in result.stdout
    assert "--allow-lifecycle" in result.stdout
    assert "--max-tokens" in result.stdout
    assert "--max-content-size" in result.stdout
