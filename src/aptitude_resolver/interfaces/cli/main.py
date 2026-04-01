"""Console entrypoint for the Aptitude CLI."""

from __future__ import annotations

import sys

from aptitude_resolver.interfaces.cli.app import app


def run_tui_app() -> None:
    """Launch the full-screen Textual interface."""

    from aptitude_resolver.interfaces.tui.app import run_tui_app as launch

    launch()


def main() -> None:
    """Run the Typer CLI app."""

    if len(sys.argv) == 1:
        run_tui_app()
        return
    app()


if __name__ == "__main__":
    main()
