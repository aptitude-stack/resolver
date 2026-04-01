from __future__ import annotations

from aptitude_resolver.interfaces.cli import main as main_module


def test_main_launches_textual_app_when_invoked_without_subcommands(
    monkeypatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main_module.sys, "argv", ["aptitude_resolver"])
    monkeypatch.setattr(main_module, "run_tui_app", lambda: calls.append("tui"))
    monkeypatch.setattr(main_module, "aptitude_resolver", lambda: calls.append("cli"))

    main_module.main()

    assert calls == ["tui"]


def test_main_routes_help_requests_to_typer_app(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(main_module.sys, "argv", ["aptitude_resolver", "--help"])
    monkeypatch.setattr(main_module, "run_tui_app", lambda: calls.append("tui"))
    monkeypatch.setattr(main_module, "aptitude_resolver", lambda: calls.append("cli"))

    main_module.main()

    assert calls == ["cli"]


def test_main_routes_subcommands_to_typer_app(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        main_module.sys, "argv", ["aptitude_resolver", "install", "python lint"]
    )
    monkeypatch.setattr(main_module, "run_tui_app", lambda: calls.append("tui"))
    monkeypatch.setattr(main_module, "aptitude_resolver", lambda: calls.append("cli"))

    main_module.main()

    assert calls == ["cli"]
