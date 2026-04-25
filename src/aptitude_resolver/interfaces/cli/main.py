"""Console entrypoint for the Aptitude CLI."""

from __future__ import annotations

import sys

from aptitude_resolver.interfaces.cli.app import app, configure_help_surfaces
from aptitude_resolver.interfaces.cli.wizard import (
    can_launch_cli_wizard,
    run_cli_wizard,
)


def main() -> None:
    """Run the Aptitude CLI."""

    configure_help_surfaces()
    if len(sys.argv) == 1 and can_launch_cli_wizard():
        run_cli_wizard()
        return
    app()


if __name__ == "__main__":
    main()
