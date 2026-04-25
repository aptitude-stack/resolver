"""Error formatting helpers for the Aptitude MCP interface."""

from __future__ import annotations

from aptitude_resolver.domain.errors import AptitudeResolverError
from aptitude_resolver.interfaces.cli.support import format_cli_error


def format_mcp_error(error: AptitudeResolverError) -> str:
    """Return an actionable MCP-facing resolver error."""

    return format_cli_error(error)
