from __future__ import annotations

from typer.testing import CliRunner

from aptitude_client.interfaces.cli import app as app_module


runner = CliRunner()


def test_cli_help_exposes_install_and_sync_as_primary_commands() -> None:
    result = runner.invoke(app_module.app, ["--help"])

    assert result.exit_code == 0
    assert "install" in result.stdout
    assert "sync" in result.stdout
    assert "resolve" not in result.stdout


def test_cli_install_help_exposes_selection_preference_flags() -> None:
    result = runner.invoke(app_module.app, ["install", "--help"])

    assert result.exit_code == 0
    assert "--prefer" in result.stdout
    assert "--interaction-mode" in result.stdout
