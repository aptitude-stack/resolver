"""FastMCP server factory for Aptitude."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from aptitude_resolver.application.composition import (
    build_effective_policy_report,
    build_inspect_use_case,
    build_install_use_case,
    build_resolve_use_case,
    build_search_use_case,
    build_sync_use_case,
)
from aptitude_resolver.application.dto import (
    InspectSkillRequestDto,
    InstallRequestDto,
    ResolveQueryRequestDto,
    SearchSkillsRequestDto,
    SyncRequestDto,
)
from aptitude_resolver.domain.errors import AptitudeResolverError
from aptitude_resolver.interfaces.cli.catalog import build_manifest_text
from aptitude_resolver.interfaces.mcp.errors import format_mcp_error
from aptitude_resolver.interfaces.mcp.formatting import (
    format_response,
    paginate_items,
)
from aptitude_resolver.interfaces.mcp.models import (
    InspectSkillInput,
    InstallSkillInput,
    ResponseFormat,
    ResolveSkillInput,
    SearchSkillsInput,
    ShowPolicyInput,
    SyncLockInput,
)

TOOL_ANNOTATIONS: dict[str, ToolAnnotations] = {
    "aptitude_search_skills": ToolAnnotations(
        title="Search Aptitude Skills",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    "aptitude_inspect_skill": ToolAnnotations(
        title="Inspect Aptitude Skill",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    "aptitude_resolve_skill": ToolAnnotations(
        title="Resolve Aptitude Skill",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
    "aptitude_show_policy": ToolAnnotations(
        title="Show Aptitude Policy",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    "aptitude_install_skill": ToolAnnotations(
        title="Install Aptitude Skill",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    ),
    "aptitude_sync_lock": ToolAnnotations(
        title="Sync Aptitude Lock",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    ),
}


class _SearchUseCase(Protocol):
    def execute(self, request: SearchSkillsRequestDto): ...


class _InspectUseCase(Protocol):
    def execute(self, request: InspectSkillRequestDto): ...


class _ResolveUseCase(Protocol):
    def execute(self, request: ResolveQueryRequestDto): ...


class _InstallUseCase(Protocol):
    def execute(self, request: InstallRequestDto): ...


class _SyncUseCase(Protocol):
    def execute(self, request: SyncRequestDto): ...


SearchBuilder = Callable[..., tuple[_SearchUseCase, Callable[[], None]]]
InspectBuilder = Callable[..., tuple[_InspectUseCase, Callable[[], None]]]
ResolveBuilder = Callable[..., tuple[_ResolveUseCase, Callable[[], None]]]
InstallBuilder = Callable[..., tuple[_InstallUseCase, Callable[[], None]]]
SyncBuilder = Callable[..., tuple[_SyncUseCase, Callable[[], None]]]
PolicyReportBuilder = Callable[..., Any]


class AptitudeMcpAdapter:
    """Thin adapter from MCP request models to application use cases."""

    def __init__(
        self,
        *,
        search_builder: SearchBuilder = build_search_use_case,
        inspect_builder: InspectBuilder = build_inspect_use_case,
        resolve_builder: ResolveBuilder = build_resolve_use_case,
        install_builder: InstallBuilder = build_install_use_case,
        sync_builder: SyncBuilder = build_sync_use_case,
        policy_report_builder: PolicyReportBuilder = build_effective_policy_report,
    ) -> None:
        self._search_builder = search_builder
        self._inspect_builder = inspect_builder
        self._resolve_builder = resolve_builder
        self._install_builder = install_builder
        self._sync_builder = sync_builder
        self._policy_report_builder = policy_report_builder

    def search_skills(self, params: SearchSkillsInput) -> str:
        use_case, close = self._search_builder(**_workflow_kwargs(params))
        try:
            result = use_case.execute(SearchSkillsRequestDto(query=params.query))
            paginated = paginate_items(
                result.candidates,
                limit=params.limit,
                offset=params.offset,
                key="candidates",
            )
            payload = {
                "requested_query": result.requested_query,
                "status": result.status,
                **paginated,
                "trace": result.trace,
            }
            return format_response(payload, params.response_format)
        except AptitudeResolverError as exc:
            return _error_response(exc)
        finally:
            close()

    def inspect_skill(self, params: InspectSkillInput) -> str:
        use_case, close = self._inspect_builder(**_workflow_kwargs(params))
        try:
            result = use_case.execute(
                InspectSkillRequestDto(
                    query=params.query,
                    version=params.version,
                    select_slug=params.select_slug,
                    interaction_mode=params.interaction_mode,
                    prompt_capable=False,
                    selection_source="mcp",
                    preview_char_limit=params.preview_char_limit,
                )
            )
            return format_response(result, params.response_format)
        except AptitudeResolverError as exc:
            return _error_response(exc)
        finally:
            close()

    def resolve_skill(self, params: ResolveSkillInput) -> str:
        use_case, close = self._resolve_builder(**_workflow_kwargs(params))
        try:
            result = use_case.execute(
                ResolveQueryRequestDto(
                    query=params.query,
                    version=params.version,
                    select_slug=params.select_slug,
                    interaction_mode=params.interaction_mode,
                    prompt_capable=False,
                    selection_source="mcp",
                )
            )
            return format_response(result, params.response_format)
        except AptitudeResolverError as exc:
            return _error_response(exc)
        finally:
            close()

    def show_policy(self, params: ShowPolicyInput) -> str:
        try:
            result = self._policy_report_builder(cwd=_resolve_optional_path(params.cwd))
            return format_response(result, params.response_format)
        except AptitudeResolverError as exc:
            return _error_response(exc)

    def install_skill(self, params: InstallSkillInput) -> str:
        target = _resolve_required_path(params.target, field_name="target")
        use_case, close = self._install_builder(**_workflow_kwargs(params))
        try:
            result = use_case.execute(
                InstallRequestDto(
                    query=params.query,
                    target=target,
                    version=params.version,
                    select_slug=params.select_slug,
                    interaction_mode=params.interaction_mode,
                    prompt_capable=False,
                    selection_source="mcp",
                )
            )
            return format_response(result, params.response_format)
        except AptitudeResolverError as exc:
            return _error_response(exc)
        finally:
            close()

    def sync_lock(self, params: SyncLockInput) -> str:
        lock_path = _resolve_required_path(params.lock_path, field_name="lock_path")
        target = _resolve_required_path(params.target, field_name="target")
        use_case, close = self._sync_builder()
        try:
            result = use_case.execute(
                SyncRequestDto(lock_path=lock_path, target=target)
            )
            return format_response(result, params.response_format)
        except AptitudeResolverError as exc:
            return _error_response(exc)
        finally:
            close()


def create_server(adapter: AptitudeMcpAdapter | None = None) -> FastMCP:
    """Create the Aptitude MCP server."""

    active_adapter = adapter or AptitudeMcpAdapter()
    mcp = FastMCP(
        "aptitude_mcp",
        instructions=(
            "Use Aptitude tools to search, inspect, resolve, install, and sync AI "
            "skills. Resolve and inspect before invoking install or sync because "
            "those tools write to the local filesystem."
        ),
    )

    @mcp.tool(
        name="aptitude_search_skills",
        annotations=TOOL_ANNOTATIONS["aptitude_search_skills"],
    )
    def aptitude_search_skills(params: SearchSkillsInput) -> str:
        """Search Aptitude registry candidates without resolving or installing."""

        return active_adapter.search_skills(params)

    @mcp.tool(
        name="aptitude_inspect_skill",
        annotations=TOOL_ANNOTATIONS["aptitude_inspect_skill"],
    )
    def aptitude_inspect_skill(params: InspectSkillInput) -> str:
        """Inspect one selected Aptitude skill and return metadata and preview content."""

        return active_adapter.inspect_skill(params)

    @mcp.tool(
        name="aptitude_resolve_skill",
        annotations=TOOL_ANNOTATIONS["aptitude_resolve_skill"],
    )
    def aptitude_resolve_skill(params: ResolveSkillInput) -> str:
        """Resolve a skill query into a deterministic graph, lockfile, and plan."""

        return active_adapter.resolve_skill(params)

    @mcp.tool(
        name="aptitude_show_policy",
        annotations=TOOL_ANNOTATIONS["aptitude_show_policy"],
    )
    def aptitude_show_policy(params: ShowPolicyInput) -> str:
        """Show effective Aptitude selection preferences, policy, and config layers."""

        return active_adapter.show_policy(params)

    @mcp.tool(
        name="aptitude_install_skill",
        annotations=TOOL_ANNOTATIONS["aptitude_install_skill"],
    )
    def aptitude_install_skill(params: InstallSkillInput) -> str:
        """Resolve and materialize a skill query into an explicit local target path."""

        return active_adapter.install_skill(params)

    @mcp.tool(
        name="aptitude_sync_lock",
        annotations=TOOL_ANNOTATIONS["aptitude_sync_lock"],
    )
    def aptitude_sync_lock(params: SyncLockInput) -> str:
        """Materialize an existing Aptitude lockfile into an explicit local target path."""

        return active_adapter.sync_lock(params)

    @mcp.resource("aptitude://manifest")
    def aptitude_manifest() -> str:
        """Return the Aptitude CLI capability manifest."""

        return build_manifest_text()

    @mcp.resource("aptitude://policy/effective")
    def aptitude_effective_policy() -> str:
        """Return the effective Aptitude policy for the current workspace."""

        return active_adapter.show_policy(
            ShowPolicyInput(response_format=ResponseFormat.MARKDOWN)
        )

    @mcp.resource("aptitude://docs/architecture")
    def aptitude_architecture_docs() -> str:
        """Return the Aptitude architecture overview."""

        return _read_repo_text("docs/architecture/system-overview.md")

    @mcp.resource("aptitude://docs/cli-interface")
    def aptitude_cli_interface_docs() -> str:
        """Return the Aptitude CLI interface contract."""

        return _read_repo_text("docs/architecture/cli-interface.md")

    @mcp.prompt("aptitude_plan_install")
    def aptitude_plan_install(query: str) -> str:
        """Create a prompt for planning an Aptitude install."""

        return (
            f"Resolve `{query}` with `aptitude_resolve_skill`, review the selected "
            "coordinate, governance, lockfile, and execution plan, then ask for "
            "confirmation before calling `aptitude_install_skill` with an explicit target."
        )

    @mcp.prompt("aptitude_compare_candidates")
    def aptitude_compare_candidates(query: str) -> str:
        """Create a prompt for comparing Aptitude discovery candidates."""

        return (
            f"Search `{query}` with `aptitude_search_skills`, inspect promising "
            "candidates with `aptitude_inspect_skill`, and compare lifecycle, trust, "
            "runtime, labels, token estimate, and selection details."
        )

    @mcp.prompt("aptitude_sync_from_lock")
    def aptitude_sync_from_lock(lock_path: str, target: str) -> str:
        """Create a prompt for lock-driven sync."""

        return (
            f"Before syncing, inspect the lock path `{lock_path}` and target `{target}`. "
            "Use `aptitude_sync_lock` only with the explicit lock_path and target provided "
            "by the user."
        )

    return mcp


def _workflow_kwargs(params: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    field_map = {
        "selection_profile": "selection_profile_override",
        "interaction_mode": "interaction_mode_override",
        "allowed_trust_tiers": "allowed_trust_tiers_override",
        "allowed_lifecycle_statuses": "allowed_lifecycle_statuses_override",
        "max_token_estimate": "max_token_estimate_override",
        "max_content_size_bytes": "max_content_size_bytes_override",
    }
    for source, target in field_map.items():
        value = getattr(params, source, None)
        if value is not None:
            kwargs[target] = value
    return kwargs


def _resolve_required_path(path: Path, *, field_name: str) -> Path:
    raw = str(path).strip()
    if not raw:
        raise ValueError(f"{field_name} is required")
    return Path(raw).expanduser().resolve()


def _resolve_optional_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return _resolve_required_path(path, field_name="cwd")


def _error_response(error: AptitudeResolverError) -> str:
    return "Error: " + format_mcp_error(error)


def _read_repo_text(relative_path: str) -> str:
    root = Path(__file__).resolve().parents[4]
    return (root / relative_path).read_text(encoding="utf-8")
