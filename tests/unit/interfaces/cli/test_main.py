from __future__ import annotations

from aptitude_resolver.interfaces.cli import main as main_module


def test_main_launches_cli_wizard_when_invoked_without_subcommands(
    monkeypatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main_module.sys, "argv", ["aptitude"])
    monkeypatch.setattr(main_module, "can_launch_cli_wizard", lambda: True)
    monkeypatch.setattr(main_module, "run_cli_wizard", lambda: calls.append("wizard"))
    monkeypatch.setattr(main_module, "app", lambda: calls.append("cli"))

    main_module.main()

    assert calls == ["wizard"]


def test_main_routes_no_arg_invocation_to_typer_app_when_wizard_ui_is_unavailable(
    monkeypatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main_module.sys, "argv", ["aptitude"])
    monkeypatch.setattr(main_module, "can_launch_cli_wizard", lambda: False)
    monkeypatch.setattr(main_module, "run_cli_wizard", lambda: calls.append("wizard"))
    monkeypatch.setattr(main_module, "app", lambda: calls.append("cli"))

    main_module.main()

    assert calls == ["cli"]


def test_main_routes_help_requests_to_typer_app(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main_module.sys, "argv", ["aptitude", "--help"])
    monkeypatch.setattr(main_module, "run_cli_wizard", lambda: calls.append("wizard"))
    monkeypatch.setattr(main_module, "app", lambda: calls.append("cli"))

    main_module.main()

    assert calls == ["cli"]


def test_main_routes_subcommands_to_typer_app(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main_module.sys, "argv", ["aptitude", "install", "python lint"])
    monkeypatch.setattr(main_module, "run_cli_wizard", lambda: calls.append("wizard"))
    monkeypatch.setattr(main_module, "app", lambda: calls.append("cli"))

    main_module.main()

    assert calls == ["cli"]
