from __future__ import annotations

from pathlib import Path

from aptitude_resolver.interfaces.mcp import main


def test_main_entrypoint_invokes_stdio_server(monkeypatch) -> None:
    calls: list[str] = []

    class FakeServer:
        def run(self, *, transport: str) -> None:
            calls.append(transport)

    monkeypatch.setattr(main, "create_server", lambda: FakeServer())

    main.main()

    assert calls == ["stdio"]


def test_pyproject_exposes_mcp_entrypoint_and_python_baseline() -> None:
    pyproject_path = Path(__file__).resolve().parents[4] / "pyproject.toml"
    pyproject = pyproject_path.read_text(encoding="utf-8")

    assert 'requires-python = ">=3.10"' in pyproject
    assert (
        'aptitude-mcp = "aptitude_resolver.interfaces.mcp.main:main"'
        in pyproject
    )
