from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from aptitude_resolver.application.dto import (
    ConfigLayerDto,
    DiscoveryCandidateDto,
    EffectivePolicyReportDto,
    ExecutionPlanDto,
    InstallResultDto,
    InstalledSkillDto,
    LockRootDto,
    LockfileDto,
    PolicyConfigSnapshotDto,
    PolicyMergeSemanticsDto,
    ResolveCoordinateDto,
    ResolveQueryResultDto,
    SearchSkillsResultDto,
    SelectionConfigSnapshotDto,
    SyncResultDto,
)
from aptitude_resolver.domain.errors import InvalidLockfileError
from aptitude_resolver.interfaces.mcp.models import (
    InstallSkillInput,
    ResponseFormat,
    ResolveSkillInput,
    SearchSkillsInput,
    ShowPolicyInput,
    SyncLockInput,
)
from aptitude_resolver.interfaces.mcp.server import (
    AptitudeMcpAdapter,
    TOOL_ANNOTATIONS,
    create_server,
)


class RecordingUseCase:
    def __init__(self, result: Any | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.requests: list[Any] = []

    def execute(self, request: Any) -> Any:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


class RecordingBuilder:
    def __init__(self, use_case: RecordingUseCase) -> None:
        self.use_case = use_case
        self.kwargs: dict[str, Any] | None = None
        self.closed = False

    def __call__(self, **kwargs: Any) -> tuple[RecordingUseCase, Any]:
        self.kwargs = kwargs
        return self.use_case, self.close

    def close(self) -> None:
        self.closed = True


def _candidate(slug: str, position: int = 1) -> DiscoveryCandidateDto:
    return DiscoveryCandidateDto(
        slug=slug,
        version="1.0.0",
        name=slug.replace("-", " ").title(),
        description="Test skill",
        lifecycle_status="stable",
        trust_tier="verified",
        published_at="2026-04-24T00:00:00Z",
        ranking_position=position,
    )


def _policy_report() -> EffectivePolicyReportDto:
    return EffectivePolicyReportDto(
        cwd=str(Path.cwd()),
        effective_selection=SelectionConfigSnapshotDto(
            profile="balanced",
            interaction_mode="never",
        ),
        effective_policy=PolicyConfigSnapshotDto(
            allowed_lifecycle_statuses=["stable"],
            allowed_trust_tiers=["verified"],
        ),
        layers=[
            ConfigLayerDto(
                source="default",
                label="default",
                active=True,
            )
        ],
        semantics=PolicyMergeSemanticsDto(
            selection_precedence=["default"],
            policy_application_order=["default"],
            selection_rule="last value wins",
            policy_rule="stricter values win",
        ),
    )


def test_search_skills_paginates_and_closes_builder() -> None:
    use_case = RecordingUseCase(
        SearchSkillsResultDto(
            requested_query="postman",
            status="found",
            candidates=[_candidate("one", 1), _candidate("two", 2)],
        )
    )
    builder = RecordingBuilder(use_case)
    adapter = AptitudeMcpAdapter(search_builder=builder)

    response = adapter.search_skills(
        SearchSkillsInput(
            query="postman",
            limit=1,
            response_format=ResponseFormat.JSON,
        )
    )
    payload = json.loads(response)

    assert payload["count"] == 1
    assert payload["has_more"] is True
    assert payload["candidates"][0]["slug"] == "one"
    assert builder.closed is True
    assert builder.kwargs == {"interaction_mode_override": "never"}
    assert use_case.requests[0].query == "postman"


def test_resolve_skill_uses_non_interactive_mcp_selection_source() -> None:
    use_case = RecordingUseCase(
        ResolveQueryResultDto(
            requested_query="postman",
            status="resolved",
            selected_coordinate=ResolveCoordinateDto(
                slug="postman-primary",
                version="1.0.0",
            ),
        )
    )
    builder = RecordingBuilder(use_case)
    adapter = AptitudeMcpAdapter(resolve_builder=builder)

    response = adapter.resolve_skill(
        ResolveSkillInput(query="postman", response_format=ResponseFormat.JSON)
    )
    payload = json.loads(response)

    assert payload["selected_coordinate"]["slug"] == "postman-primary"
    assert use_case.requests[0].prompt_capable is False
    assert use_case.requests[0].selection_source == "mcp"
    assert builder.closed is True


def test_install_skill_resolves_explicit_target_and_closes_builder(tmp_path: Path) -> None:
    use_case = RecordingUseCase(
        InstallResultDto(
            requested_query="postman",
            status="installed",
            selected_coordinate=ResolveCoordinateDto(
                slug="postman-primary",
                version="1.0.0",
            ),
            installed_skills=[
                InstalledSkillDto(
                    slug="postman-primary",
                    version="1.0.0",
                    install_path=str(tmp_path / "skill"),
                )
            ],
            materialized_root=str(tmp_path),
        )
    )
    builder = RecordingBuilder(use_case)
    adapter = AptitudeMcpAdapter(install_builder=builder)

    response = adapter.install_skill(
        InstallSkillInput(
            query="postman",
            target=tmp_path / "target",
            response_format=ResponseFormat.JSON,
        )
    )
    payload = json.loads(response)

    assert payload["status"] == "installed"
    assert use_case.requests[0].target.is_absolute()
    assert use_case.requests[0].selection_source == "mcp"
    assert builder.closed is True


def test_sync_lock_resolves_paths_and_closes_builder(tmp_path: Path) -> None:
    use_case = RecordingUseCase(
        SyncResultDto(
            lock_path=str(tmp_path / "aptitude.lock.json"),
            requested_query="postman",
            status="synced",
            lockfile=LockfileDto(
                version=1,
                root=LockRootDto(
                    request="postman",
                    selected_node_id="postman-primary@1.0.0",
                    selection_mode="exact",
                ),
            ),
            execution_plan=ExecutionPlanDto(),
            materialized_root=str(tmp_path / "target"),
        )
    )
    builder = RecordingBuilder(use_case)
    adapter = AptitudeMcpAdapter(sync_builder=builder)

    response = adapter.sync_lock(
        SyncLockInput(
            lock_path=tmp_path / "aptitude.lock.json",
            target=tmp_path / "target",
            response_format=ResponseFormat.JSON,
        )
    )
    payload = json.loads(response)

    assert payload["status"] == "synced"
    assert use_case.requests[0].lock_path.is_absolute()
    assert use_case.requests[0].target.is_absolute()
    assert builder.closed is True


def test_adapter_returns_actionable_resolver_error_and_closes() -> None:
    use_case = RecordingUseCase(error=InvalidLockfileError("Lockfile is not valid JSON."))
    builder = RecordingBuilder(use_case)
    adapter = AptitudeMcpAdapter(sync_builder=builder)

    response = adapter.sync_lock(
        SyncLockInput(
            lock_path=Path("aptitude.lock.json"),
            target=Path("target"),
        )
    )

    assert response.startswith("Error: Lockfile could not be loaded.")
    assert builder.closed is True


def test_show_policy_uses_report_builder() -> None:
    adapter = AptitudeMcpAdapter(policy_report_builder=lambda **_: _policy_report())

    response = adapter.show_policy(ShowPolicyInput(response_format=ResponseFormat.JSON))
    payload = json.loads(response)

    assert payload["effective_selection"]["profile"] == "balanced"
    assert payload["effective_policy"]["allowed_trust_tiers"] == ["verified"]


def test_tool_annotations_distinguish_read_only_and_mutating_tools() -> None:
    assert TOOL_ANNOTATIONS["aptitude_search_skills"].readOnlyHint is True
    assert TOOL_ANNOTATIONS["aptitude_search_skills"].destructiveHint is False
    assert TOOL_ANNOTATIONS["aptitude_install_skill"].readOnlyHint is False
    assert TOOL_ANNOTATIONS["aptitude_install_skill"].destructiveHint is True
    assert TOOL_ANNOTATIONS["aptitude_sync_lock"].destructiveHint is True


def test_create_server_registers_tools_resources_and_prompts() -> None:
    async def list_names() -> tuple[list[str], list[str], list[str]]:
        server = create_server(
            AptitudeMcpAdapter(policy_report_builder=lambda **_: _policy_report())
        )
        tools = await server.list_tools()
        resources = await server.list_resources()
        prompts = await server.list_prompts()
        return (
            [tool.name for tool in tools],
            [str(resource.uri) for resource in resources],
            [prompt.name for prompt in prompts],
        )

    tool_names, resource_uris, prompt_names = asyncio.run(list_names())

    assert "aptitude_search_skills" in tool_names
    assert "aptitude_install_skill" in tool_names
    assert "aptitude://manifest" in resource_uris
    assert "aptitude://docs/architecture" in resource_uris
    assert "aptitude_plan_install" in prompt_names
