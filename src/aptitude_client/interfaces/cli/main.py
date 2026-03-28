"""Console entrypoint for the Aptitude CLI."""

from __future__ import annotations

from aptitude_client.interfaces.cli.app import app


def main() -> None:
    """Run the Typer CLI app."""

    app()


if __name__ == "__main__":
    main()
