from __future__ import annotations

from pathlib import Path
from typing import Callable, Generic, TypeVar, cast

import pytest

from aptitude.application.dto import InstallRequestDto, ResolveQueryRequestDto
from aptitude.interfaces.shared.install_workflow import (
    InstallBuilder,
    InstallWorkflowOptions,
    InstallWorkflowService,
    ResolveBuilder,
)

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


class QueueUseCase(Generic[RequestT, ResponseT]):
    def __init__(
        self,
        responses: list[ResponseT] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.requests: list[RequestT] = []

    def execute(self, request: RequestT) -> ResponseT:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.responses
        return self.responses.pop(0)


def test_resolve_query_applies_builder_overrides_and_closes() -> None:
    response = object()
    use_case = QueueUseCase[ResolveQueryRequestDto, object](responses=[response])
    builder_kwargs: dict[str, object] = {}
    close_calls: list[str] = []

    def build_resolve_use_case(
        **kwargs: object,
    ) -> tuple[QueueUseCase[ResolveQueryRequestDto, object], Callable[[], None]]:
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    service = InstallWorkflowService(
        resolve_builder=cast(ResolveBuilder, build_resolve_use_case)
    )

    result = service.resolve_query(
        query="python lint",
        version="1.2.3",
        select_slug="python.lint",
        interaction_mode=None,
        prompt_capable=True,
        selection_source=None,
        options=InstallWorkflowOptions(
            selection_profile="high-trust",
            interaction_mode="always",
        ),
    )

    assert result is response
    assert builder_kwargs == {
        "selection_profile_override": "high-trust",
        "interaction_mode_override": "always",
    }
    assert use_case.requests[0].query == "python lint"
    assert use_case.requests[0].version == "1.2.3"
    assert use_case.requests[0].select_slug == "python.lint"
    assert use_case.requests[0].prompt_capable is True
    assert close_calls == ["closed"]


def test_install_query_closes_builder_when_use_case_raises() -> None:
    use_case = QueueUseCase[InstallRequestDto, object](error=RuntimeError("boom"))
    close_calls: list[str] = []

    def build_install_use_case(
        **_: object,
    ) -> tuple[QueueUseCase[InstallRequestDto, object], Callable[[], None]]:
        return use_case, lambda: close_calls.append("closed")

    service = InstallWorkflowService(
        install_builder=cast(InstallBuilder, build_install_use_case)
    )

    with pytest.raises(RuntimeError, match="boom"):
        service.install_query(
            query="python lint",
            version=None,
            select_slug=None,
            target=Path("skill_demo"),
            interaction_mode=None,
            prompt_capable=False,
            selection_source=None,
            options=InstallWorkflowOptions(),
        )

    assert close_calls == ["closed"]


def test_install_query_applies_builder_overrides_and_forwards_install_controls() -> (
    None
):
    response = object()
    use_case = QueueUseCase[InstallRequestDto, object](responses=[response])
    builder_kwargs: dict[str, object] = {}
    close_calls: list[str] = []
    target = Path("project/.aptitude")

    def build_install_use_case(
        **kwargs: object,
    ) -> tuple[QueueUseCase[InstallRequestDto, object], Callable[[], None]]:
        builder_kwargs.update(kwargs)
        return use_case, lambda: close_calls.append("closed")

    service = InstallWorkflowService(
        install_builder=cast(InstallBuilder, build_install_use_case)
    )

    result = service.install_query(
        query="python lint",
        version="1.2.3",
        select_slug="python.lint",
        target=target,
        interaction_mode="never",
        prompt_capable=False,
        selection_source="cli_flag",
        options=InstallWorkflowOptions(
            selection_profile="low-cost",
            interaction_mode="never",
            allowed_trust_tiers=["verified", "internal"],
            allowed_lifecycle_statuses=["published"],
            max_token_estimate=300,
            max_content_size_bytes=4096,
        ),
    )

    assert result is response
    assert builder_kwargs == {
        "selection_profile_override": "low-cost",
        "interaction_mode_override": "never",
        "allowed_trust_tiers_override": ["verified", "internal"],
        "allowed_lifecycle_statuses_override": ["published"],
        "max_token_estimate_override": 300,
        "max_content_size_bytes_override": 4096,
    }
    assert use_case.requests[0].target == target
    assert use_case.requests[0].interaction_mode == "never"
    assert use_case.requests[0].prompt_capable is False
    assert use_case.requests[0].selection_source == "cli_flag"
    assert close_calls == ["closed"]
