"""Typer application for the Aptitude CLI."""

from __future__ import annotations

import json
from collections.abc import Callable

import typer

from aptitude_client.application.dto import ResolveQueryRequestDto
from aptitude_client.application.use_cases import ResolveSkillQueryUseCase
from aptitude_client.domain.errors import AptitudeClientError
from aptitude_client.registry import RegistryClient
from aptitude_client.shared.config import Settings


app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Aptitude CLI root command group."""


def build_resolve_use_case() -> tuple[ResolveSkillQueryUseCase, Callable[[], None]]:
    """Create the resolve use case and its cleanup hook."""

    registry_client = RegistryClient(Settings())
    return ResolveSkillQueryUseCase(registry_client), registry_client.close


def _format_error(error: AptitudeClientError) -> str:
    return json.dumps(
        {
            "error": error.to_payload(),
        },
        indent=2,
    )


@app.command()
def resolve(
    query: str,
    version: str | None = typer.Option(
        None,
        "--version",
        help="Exact immutable skill version. Still required when using discovery because the server exposes no version lookup route.",
    ),
) -> None:
    """Resolve a skill query and print a stable JSON result."""

    use_case, close = build_resolve_use_case()

    try:
        result = use_case.execute(ResolveQueryRequestDto(query=query, version=version))
    except AptitudeClientError as exc:
        typer.echo(_format_error(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        close()

    typer.echo(result.model_dump_json(indent=2, exclude_none=True))
