"""Shared orchestration helpers for CLI and wizard flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Protocol

from aptitude_resolver.application.composition import (
    build_install_use_case,
    build_resolve_use_case,
    build_search_use_case,
    build_sync_use_case,
)
from aptitude_resolver.application.dto import (
    InstallRequestDto,
    InstallResultDto,
    ResolveQueryRequestDto,
    ResolveQueryResultDto,
    SearchSkillsRequestDto,
    SearchSkillsResultDto,
    SyncRequestDto,
    SyncResultDto,
)

InteractionMode = Literal["auto", "always", "never"]


class ResolveWorkflowUseCase(Protocol):
    def execute(self, request: ResolveQueryRequestDto) -> ResolveQueryResultDto: ...


class InstallWorkflowUseCase(Protocol):
    def execute(
        self,
        request: InstallRequestDto,
        *,
        review_plan: Callable[[ResolveQueryResultDto], None] | None = None,
    ) -> InstallResultDto: ...


class SearchWorkflowUseCase(Protocol):
    def execute(self, request: SearchSkillsRequestDto) -> SearchSkillsResultDto: ...


class SyncWorkflowUseCase(Protocol):
    def execute(self, request: SyncRequestDto) -> SyncResultDto: ...


ResolveBuilder = Callable[..., tuple[ResolveWorkflowUseCase, Callable[[], None]]]
InstallBuilder = Callable[..., tuple[InstallWorkflowUseCase, Callable[[], None]]]
SearchBuilder = Callable[..., tuple[SearchWorkflowUseCase, Callable[[], None]]]
SyncBuilder = Callable[[], tuple[SyncWorkflowUseCase, Callable[[], None]]]


@dataclass(frozen=True)
class InstallWorkflowOptions:
    """Optional CLI and wizard overrides for planning and install use cases."""

    selection_profile: str | None = None
    interaction_mode: InteractionMode | None = None
    allowed_trust_tiers: list[str] | None = None
    allowed_lifecycle_statuses: list[str] | None = None
    max_token_estimate: int | None = None
    max_content_size_bytes: int | None = None
    cwd: Path | None = None

    def build_kwargs(self) -> dict[str, object]:
        """Return composition kwargs for the configured overrides."""

        kwargs: dict[str, object] = {}
        if self.selection_profile is not None:
            kwargs["selection_profile_override"] = self.selection_profile
        if self.interaction_mode is not None:
            kwargs["interaction_mode_override"] = self.interaction_mode
        if self.allowed_trust_tiers is not None:
            kwargs["allowed_trust_tiers_override"] = self.allowed_trust_tiers
        if self.allowed_lifecycle_statuses is not None:
            kwargs["allowed_lifecycle_statuses_override"] = (
                self.allowed_lifecycle_statuses
            )
        if self.max_token_estimate is not None:
            kwargs["max_token_estimate_override"] = self.max_token_estimate
        if self.max_content_size_bytes is not None:
            kwargs["max_content_size_bytes_override"] = self.max_content_size_bytes
        if self.cwd is not None:
            kwargs["cwd"] = self.cwd
        return kwargs


class InstallWorkflowService:
    """Run resolve/install/sync workflows with shared builder cleanup."""

    def __init__(
        self,
        *,
        resolve_builder: ResolveBuilder = build_resolve_use_case,
        install_builder: InstallBuilder = build_install_use_case,
        search_builder: SearchBuilder = build_search_use_case,
        sync_builder: SyncBuilder = build_sync_use_case,
    ) -> None:
        self._resolve_builder = resolve_builder
        self._install_builder = install_builder
        self._search_builder = search_builder
        self._sync_builder = sync_builder

    def search_query(
        self,
        *,
        query: str,
        options: InstallWorkflowOptions | None = None,
    ) -> SearchSkillsResultDto:
        """Execute discovery-only search with shared builder cleanup."""

        use_case, close = self.prepare_search(options=options)
        try:
            return self.execute_search(use_case, query=query)
        finally:
            close()

    def resolve_query(
        self,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
        options: InstallWorkflowOptions | None = None,
    ) -> ResolveQueryResultDto:
        """Execute resolve with shared override handling and cleanup."""

        use_case, close = self.prepare_resolve(options=options)
        try:
            return self.execute_resolve(
                use_case,
                query=query,
                version=version,
                select_slug=select_slug,
                interaction_mode=interaction_mode,
                prompt_capable=prompt_capable,
                selection_source=selection_source,
            )
        finally:
            close()

    def install_query(
        self,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        target: Path | None,
        exact: bool = False,
        agents: list[str] | None = None,
        scope: Literal["project", "global", "custom"] = "project",
        export_root: Path | None = None,
        cwd: Path | None = None,
        interaction_mode: InteractionMode | None = None,
        prompt_capable: bool = False,
        selection_source: str | None = None,
        options: InstallWorkflowOptions | None = None,
    ) -> InstallResultDto:
        """Execute install with shared override handling and cleanup."""

        use_case, close = self.prepare_install(options=options)
        try:
            return self.execute_install(
                use_case,
                query=query,
                version=version,
                select_slug=select_slug,
                target=target,
                exact=exact,
                agents=agents or ["codex"],
                scope=scope,
                export_root=export_root,
                cwd=cwd,
                interaction_mode=interaction_mode,
                prompt_capable=prompt_capable,
                selection_source=selection_source,
            )
        finally:
            close()

    def sync_lock(
        self,
        *,
        lock_path: Path,
        target: Path | None,
    ) -> SyncResultDto:
        """Execute lock replay with builder cleanup."""

        use_case, close = self._sync_builder()
        try:
            return use_case.execute(SyncRequestDto(lock_path=lock_path, target=target))
        finally:
            close()

    def prepare_resolve(
        self,
        *,
        options: InstallWorkflowOptions | None = None,
    ) -> tuple[ResolveWorkflowUseCase, Callable[[], None]]:
        """Build one reusable resolve use case with the provided overrides."""

        return self._resolve_builder(**self._build_kwargs(options))

    def prepare_search(
        self,
        *,
        options: InstallWorkflowOptions | None = None,
    ) -> tuple[SearchWorkflowUseCase, Callable[[], None]]:
        """Build one reusable search use case with the provided overrides."""

        return self._search_builder(**self._build_kwargs(options))

    def execute_search(
        self,
        use_case: SearchWorkflowUseCase,
        *,
        query: str,
    ) -> SearchSkillsResultDto:
        """Execute one prepared search use case."""

        return use_case.execute(SearchSkillsRequestDto(query=query))

    def execute_resolve(
        self,
        use_case: ResolveWorkflowUseCase,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        interaction_mode: InteractionMode | None,
        prompt_capable: bool,
        selection_source: str | None,
    ) -> ResolveQueryResultDto:
        """Execute one prepared resolve use case."""

        return use_case.execute(
            ResolveQueryRequestDto(
                query=query,
                version=version,
                select_slug=select_slug,
                interaction_mode=interaction_mode,
                prompt_capable=prompt_capable,
                selection_source=selection_source,
            )
        )

    def prepare_install(
        self,
        *,
        options: InstallWorkflowOptions | None = None,
    ) -> tuple[InstallWorkflowUseCase, Callable[[], None]]:
        """Build one reusable install use case with the provided overrides."""

        return self._install_builder(**self._build_kwargs(options))

    def execute_install(
        self,
        use_case: InstallWorkflowUseCase,
        *,
        query: str,
        version: str | None,
        select_slug: str | None,
        target: Path | None,
        exact: bool = False,
        agents: list[str] | None = None,
        scope: Literal["project", "global", "custom"] = "project",
        export_root: Path | None = None,
        cwd: Path | None = None,
        interaction_mode: InteractionMode | None = None,
        prompt_capable: bool = False,
        selection_source: str | None = None,
        review_plan: Callable[[ResolveQueryResultDto], None] | None = None,
    ) -> InstallResultDto:
        """Execute one prepared install use case."""

        request = InstallRequestDto(
            query=query,
            version=version,
            exact=exact,
            select_slug=select_slug,
            target=target,
            agents=agents or ["codex"],
            scope=scope,
            export_root=export_root,
            cwd=cwd,
            interaction_mode=interaction_mode,
            prompt_capable=prompt_capable,
            selection_source=selection_source,
        )
        if review_plan is not None:
            return use_case.execute(request, review_plan=review_plan)
        return use_case.execute(request)

    @staticmethod
    def _build_kwargs(options: InstallWorkflowOptions | None) -> dict[str, object]:
        """Return composition kwargs for the provided overrides."""

        if options is None:
            return {}
        return options.build_kwargs()
