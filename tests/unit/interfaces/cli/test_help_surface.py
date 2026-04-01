from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from aptitude.interfaces.cli import app as app_module


runner = CliRunner()


def test_cli_help_exposes_install_and_sync_as_primary_commands() -> None:
    result = runner.invoke(app_module.app, ["--help"])

    assert result.exit_code == 0
    assert "install" in result.stdout
    assert "sync" in result.stdout
    assert "manifest" in result.stdout
    assert "--version" in result.stdout
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


def test_cli_manifest_lists_public_advanced_and_global_capabilities() -> None:
    result = runner.invoke(app_module.app, ["manifest"])

    assert result.exit_code == 0
    assert (
        "────────────────────────────────────────────────────────────────"
        in result.stdout
    )
    assert "Public Commands" in result.stdout
    assert "Advanced/Internal Commands" in result.stdout
    assert "Global / Framework Flags" in result.stdout
    assert 'aptitude install "query"' in result.stdout
    assert "aptitude sync --lock aptitude.lock.json" in result.stdout
    assert "aptitude manifest" in result.stdout
    assert 'aptitude resolve "query"' in result.stdout
    assert "--prefer" in result.stdout
    assert "--lock" in result.stdout
    assert "--version" in result.stdout
    assert "--install-completion" in result.stdout
    assert "--show-completion" in result.stdout


def test_cli_version_prints_package_version() -> None:
    result = runner.invoke(app_module.app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_contributor_docs_describe_install_first_wizard_not_textual_tui() -> None:
    contents = Path("docs/contributors/development-setup.md").read_text()

    assert "Textual TUI" not in contents
    assert "install-first wizard" in contents


def test_readme_documents_manifest_command_and_wizard_first_entry() -> None:
    contents = Path("README.md").read_text()

    assert "aptitude manifest" in contents
    assert "no arguments launches the install-first wizard" in contents


def test_makefile_exposes_demo_target_that_sources_repo_env() -> None:
    makefile = Path("Makefile").read_text()

    assert "\ndemo:\n" in makefile
    assert ". ./.env" in makefile
    assert "Running Aptitude demo CLI" in makefile
    assert "Suggest:" in makefile
    assert "Postman Primary Skill" in makefile
    assert "PYTHONPATH=src .venv/bin/python -m aptitude.interfaces.cli.main" in makefile


def test_env_example_documents_required_registry_fields() -> None:
    env_example = Path(".env.example")

    assert env_example.exists()
    contents = env_example.read_text()
    assert "APTITUDE_SERVER_BASE_URL=" in contents
    assert "APTITUDE_READ_TOKEN=" in contents
