"""Console entrypoint for the Aptitude CLI."""

from __future__ import annotations

import sys

from aptitude.interfaces.cli.app import app
from aptitude.interfaces.cli.wizard import run_cli_wizard


def main() -> None:
    """Run the Aptitude CLI."""

    if len(sys.argv) == 1:
        run_cli_wizard()
        return
    app()


if __name__ == "__main__":
    main()
