"""Aptitude client CLI application."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="aptitude",
    help="Aptitude package manager for AI skills.",
    no_args_is_help=True,
)


@app.command()
def install(skill: str = typer.Argument(..., help="Skill name to install.")) -> None:
    """Install a skill (placeholder)."""
    typer.echo(f"[placeholder] install is not implemented yet (requested: {skill}).")


@app.command()
def search(query: str = typer.Argument(..., help="Search query for skills.")) -> None:
    """Search for skills (placeholder)."""
    typer.echo(f"[placeholder] search is not implemented yet (query: {query}).")


@app.command()
def inspect(skill: str = typer.Argument(..., help="Skill name to inspect.")) -> None:
    """Inspect a skill (placeholder)."""
    typer.echo(f"[placeholder] inspect is not implemented yet (requested: {skill}).")


@app.command()
def resolve(skill: str = typer.Argument(..., help="Skill name to resolve dependencies for.")) -> None:
    """Resolve dependencies for a skill (placeholder)."""
    typer.echo(f"[placeholder] resolve is not implemented yet (requested: {skill}).")


@app.command(name="list")
def list_skills() -> None:
    """List installed skills (placeholder)."""
    typer.echo("[placeholder] list is not implemented yet.")


def run() -> None:
    """Run the CLI application."""
    app()
