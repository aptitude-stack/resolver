"""Console entrypoint for the Aptitude CLI."""

from __future__ import annotations

import sys

from aptitude.interfaces.cli.app import app


def run_tui_app() -> None:
    """Launch the full-screen Textual interface."""

    from aptitude.interfaces.tui.app import run_tui_app as launch

    launch()


def main() -> None:
    """Run the Aptitude CLI."""

    if len(sys.argv) == 1:
        run_tui_app()
        return
    app()


if __name__ == "__main__":
    main()
